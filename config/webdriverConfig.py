import platform
import json
from pathlib import Path
from typing import Optional, Iterable

from loguru import logger
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from config.JsonLoadConfig import resolve_driver_exe_path, resolve_cookie_file_path

class WebDriverConfigurator:
    def __init__(
            self,
            driver_path: Optional[str] = None,
            user_data_dir: Optional[str] = None,
            additional_args: Optional[Iterable[str]] = None,
            implicit_wait_seconds: int = 10,
            cookies_file: Optional[str] = None,
            cookie_base_url: Optional[str] = None,
            platform: str = "zhihuishu",
        ):
        # 使用集中配置解析默认路径
        self.driver_path = driver_path or resolve_driver_exe_path()
        self.user_data_dir = user_data_dir
        self.additional_args = list(additional_args) if additional_args else []
        self.implicit_wait_seconds = implicit_wait_seconds
        self.cookies_file = cookies_file or resolve_cookie_file_path()
        self.platform = platform

        # 根据平台选择 Cookie 基础域名
        if cookie_base_url:
            self.cookie_base_url = cookie_base_url
        else:
            from config.platformConfig import get_platform_config
            cfg = get_platform_config(platform)
            self.cookie_base_url = cfg.COOKIE_BASE_URL

    def build(self):
        # 创建 EdgeOptions 并设置基础降噪
        options = Options()
        options.add_argument("--log-level=3")
        options.add_argument("--silent")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])  # 禁用驱动层日志
        options.add_experimental_option("useAutomationExtension", False)         # 禁用自动化扩展

        # ===== 反自动化检测规避 =====
        # 隐藏 webdriver 特征
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # 模拟真实浏览器分辨率和窗口
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-default-apps")

        # 用户数据目录（复用正常浏览器的 cookie/代理/DNS 缓存）
        if self.user_data_dir:
            options.add_argument(f"--user-data-dir={self.user_data_dir}")
        else:
            # 使用临时隔离目录，避免与正在运行的 Edge 进程冲突
            import tempfile
            temp_profile = tempfile.mkdtemp(prefix="edge_profile_")
            options.add_argument(f"--user-data-dir={temp_profile}")
            logger.debug(f"使用临时浏览器配置文件目录: {temp_profile}")

        # 额外参数
        for arg in self.additional_args:
            options.add_argument(str(arg))

        # 创建 Service 和浏览器实例
        service = Service(executable_path=self.driver_path)
        driver = webdriver.Edge(service=service, options=options)

        # 注入 anti-detect 脚本，覆盖 navigator.webdriver 等特征
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                // 覆盖 navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // 覆盖 chrome.runtime
                window.chrome = {
                    runtime: {}
                };

                // 覆盖 permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );

                // 覆盖 plugins 长度（模拟真实浏览器）
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // 覆盖 languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en']
                });

                // 覆盖 platform
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32'
                });

                // 覆盖 webdriver 属性
                const originalToString = Function.prototype.toString;
                Function.prototype.toString = function() {
                    if (this === window.chrome || this === navigator.webdriver) {
                        return 'function webdriver() { [native code] }';
                    }
                    return originalToString.call(this);
                };

                // 移除 __webdriver_script_fn 等 Selenium 注入的标记
                delete window.__webdriver_script_fn;
                delete window.__selenium_eval;
                delete window.__webdriver_script_callback;
            """
        })

        # 设置页面加载超时（30秒）
        driver.set_page_load_timeout(30)
        driver.set_script_timeout(30)

        # 隐式等待
        if self.implicit_wait_seconds and self.implicit_wait_seconds > 0:
            driver.implicitly_wait(self.implicit_wait_seconds)

        # 加载已保存的 Cookie（如果存在）
        try:
            self._load_cookies(driver)
        except Exception as e:
            logger.warning(f"加载 Cookie 时出现异常：{e}")

        return driver

    def _load_cookies(self, driver):
        if not self.cookies_file or not Path(self.cookies_file).exists():
            logger.debug("未发现 Cookie 文件，跳过加载。")
            return

        base_url = self.cookie_base_url or "about:blank"
        logger.info(f"准备从 {self.cookies_file} 加载 Cookie，目标域：{base_url}")

        # 先打开基础域，确保后续 add_cookie 域名匹配
        try:
            driver.get(base_url)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except Exception:
                logger.debug("基础域页面等待失败，但继续尝试注入 Cookie。")
        except Exception as e:
            logger.warning(f"加载 Cookie 基础域失败: {e}，尝试直接注入。")

        # 读取 Cookie 文件
        with open(self.cookies_file, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        loaded = 0
        skipped = 0
        for c in cookies:
            # 规范化可选字段，避免 add_cookie 报错
            c = dict(c)
            if "expiry" in c and c["expiry"] is not None:
                try:
                    c["expiry"] = int(c["expiry"])
                except Exception:
                    c["expiry"] = None

            cookie_domain = c.get("domain", "")

            # 如果 Cookie 有 domain 且不是当前页面域名，先导航到该域名
            if cookie_domain and cookie_domain not in driver.current_url:
                try:
                    nav_url = f"https://{cookie_domain}" if not cookie_domain.startswith("http") else cookie_domain
                    driver.get(nav_url)
                    try:
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                    except Exception:
                        pass
                except Exception:
                    pass

            try:
                driver.add_cookie(c)
                loaded += 1
            except Exception:
                # 移除 domain/path 字段后重试（适用于泛域名 Cookie）
                c.pop("domain", None)
                c.pop("path", None)
                try:
                    driver.add_cookie(c)
                    loaded += 1
                except Exception as e:
                    skipped += 1
                    logger.debug(f"跳过单条 Cookie（{skipped} 条）：{e}")

        logger.info(f"已加载 {loaded}/{len(cookies)} 条 Cookie（跳过 {skipped} 条），刷新页面以应用登录态。")
        try:
            driver.refresh()
        except Exception:
            # 某些场景 refresh 可能报错（如 about:blank），则重新访问基础域
            try:
                driver.get(base_url)
            except Exception:
                pass