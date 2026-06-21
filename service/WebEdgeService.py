import json
from pathlib import Path
from typing import Optional
from time import sleep
from loguru import logger
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

from config.webdriverConfig import WebDriverConfigurator
from config.JsonLoadConfig import resolve_cookie_file_path
from service.SolutionService import SolutionService

"⢰⡟⣡⡟⣱⣿⡿⠡⢛⣋⣥⣴⣌⢿⣿⣿⣿⣿⣷⣌⠻⢿⣿⣿⣿⣿⣿⣿"
"⠏⢼⡿⣰⡿⠿⠡⠿⠿⢯⣉⠿⣿⣿⣿⣿⣿⣿⣷⣶⣿⣦⣍⠻⢿⣿⣿⣿"
"⣼⣷⢠⠀⠀⢠⣴⡖⠀⠀⠈⠻⣿⡿⣿⣿⣿⣿⣿⣛⣯⣝⣻⣿⣶⣿⣿⣿"
"⣿⡇⣿⡷⠂⠈⡉⠀⠀⠀⣠⣴⣾⣿⣿⣿⣿⣿⣍⡤⣤⣤⣤⡀⠀⠉⠛⠿"
"⣿⢸⣿⡅⣠⣬⣥⣤⣴⣴⣿⣿⢿⣿⣿⣿⣿⣿⣟⡭⡄⣀⣉⡀⠀⠀⠀⠀"
"⡟⣿⣿⢰⣿⣿⣿⣿⣿⣿⣿⣿⣾⣿⣿⣿⣿⣿⣿⣿⣶⣦⣈⠀⠀⠀⢀⣶"
"⡧⣿⡇⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣶⣾⣿"
"⡇⣿⠃⣿⣿⣿⣿⣿⠛⠛⢫⣿⣿⣻⣻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢿⣿"
"⡇⣿⠘⡇⢻⣿⣿⣿⡆⠀⠀⠀⠀⠈⠉⠙⠻⠏⠛⠻⣿⣿⣿⣿⣿⣭⡾⢁"
"⡇⣿⠀⠘⢿⣿⣿⣿⣧⢠⣤⠀⡤⢀⣠⣀⣀⠀⠀⣼⣿⣿⣿⣿⣿⠟⣁⠉"
"⣧⢻⠀⡄⠀⠹⣿⣿⣿⡸⣿⣾⡆⣿⣿⣿⠿⣡⣾⣿⣿⣿⣿⡿⠋⠐⢡⣶"
"⣿⡘⠈⣷⠀⠀⠈⠻⣿⣷⣎⠐⠿⢟⣋⣤⣾⣿⣿⣿⡿⠟⣩⠖⢠⡬⠈⠀"
"⣿⣧⠁⢻⡇⠀⠀⠀⠈⠻⣿⣿⣿⣿⣿⣿⠿⠟⠋⠁⢀⠈⢀⡴⠈⠁⠀⠀"
"⠻⣿⣆⠘⣿⠀⠀⣀⡁⠀⠈⠙⠛⠋⠉⠀⠀⠀⠀⡀⠤⠚⠁⠄⣠"
"欸嘿嘿,一、注释又少"
"二、屎山又多"
"你看得下得去你就看吧！"
"一看一个不知声！过几天我自己都看不懂！"
"又不是造飞机大炮，差不多能跑就行啦"


class WebEdgeService:
    def __init__(
        self,
        configurator: Optional[WebDriverConfigurator] = None,
        cookies_file: Optional[str] = None,
        platform: str = "zhihuishu",
    ):
        self._shutdown_done = False
        self.cookies_file = cookies_file or resolve_cookie_file_path()
        self.configurator = configurator
        self.driver = None
        self.platform = platform
        self.solution = SolutionService(platform=platform)

        # 加载平台配置
        from config.platformConfig import get_platform_config
        self.cfg = get_platform_config(platform)

    # ---------- 浏览器初始化（延迟到输入URL后） ----------
    def _ensure_browser(self):
        """在需要时才创建浏览器实例并加载 Cookie。"""
        if self.driver is not None:
            # 检查旧会话是否仍然有效
            try:
                self.driver.current_url
                return  # 会话正常，直接复用
            except Exception:
                logger.info("浏览器会话已失效，重新创建。")
                self.driver = None

        # 检查 Cookie 文件状态
        cookies_cfg_path: Optional[str] = self.cookies_file
        try:
            p = Path(self.cookies_file)
            if not p.exists():
                logger.debug("Cookie 文件不存在，跳过加载。")
                cookies_cfg_path = None
            else:
                raw = p.read_text(encoding="utf-8").strip()
                if not raw:
                    logger.debug("Cookie 文件为空，跳过加载。")
                    cookies_cfg_path = None
                else:
                    try:
                        data = json.loads(raw)
                        if not isinstance(data, list) or len(data) == 0:
                            logger.debug("Cookie 数据为空或格式不为列表，跳过加载。")
                            cookies_cfg_path = None
                    except Exception as e:
                        logger.warning(f"Cookie 文件解析失败，跳过加载：{e}")
                        cookies_cfg_path = None
        except Exception as e:
            logger.warning(f"Cookie 文件检查异常，跳过加载：{e}")
            cookies_cfg_path = None

        # 创建 WebDriver（如果 configurator 未指定 cookie 文件，使用当前检查后的路径）
        if self.configurator is None:
            from config.webdriverConfig import WebDriverConfigurator as WDC
            self.configurator = WDC(cookies_file=cookies_cfg_path, platform=self.platform)
        else:
            # 更新 configurator 的 cookie 文件路径
            self.configurator.cookies_file = cookies_cfg_path

        self.driver = self.configurator.build()
        logger.info("浏览器已启动。")

    # ---------- 重新打开浏览器（登录后页面变动时使用） ----------
    def _reopen_browser(self):
        """关闭当前浏览器，重新创建并加载最新 Cookie。"""
        # 先保存当前 Cookie（可能包含刚登录产生的新凭据）
        try:
            if self.driver is not None:
                self._save_cookies()
        except Exception:
            pass
        # 关闭旧浏览器
        try:
            if self.driver is not None:
                self.driver.quit()
                logger.info("旧浏览器已关闭。")
        except Exception:
            pass
        self.driver = None
        # 重新创建（_ensure_browser 会从文件加载刚保存的 Cookie）
        self._ensure_browser()
        logger.info("浏览器已重新启动并加载最新凭据。")

    # ---------- Cookie ----------
    def _save_cookies(self, file_path: Optional[str] = None):
        target = file_path or self.cookies_file
        try:
            if not hasattr(self, "driver") or self.driver is None:
                logger.debug("Driver 不存在，跳过保存 Cookie。")
                return
            if getattr(self.driver, "session_id", None) is None:
                logger.debug("Driver 会话已结束，跳过保存 Cookie。")
                return
        except Exception:
            pass
        try:
            cookies = self.driver.get_cookies()
            try:
                Path(target).parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"创建Cookie目录失败: {e}")
                return
            for c in cookies:
                if "expiry" in c and c["expiry"] is not None:
                    try:
                        c["expiry"] = int(c["expiry"])
                    except Exception:
                        c["expiry"] = None
            with open(target, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存 {len(cookies)} 条 Cookie 到 {target}")
        except Exception as e:
            logger.error(f"保存 Cookie 失败: {e}")

    # ---------- Cookie 验证 ----------
    def _safe_get(self, url: str, timeout: int = 15) -> bool:
        """安全地打开网页，处理超时。"""
        try:
            self.driver.get(url)
            sleep(2)
            return True
        except TimeoutException:
            logger.warning(f"页面加载超时 ({url})，尝试刷新...")
            try:
                self.driver.refresh()
                sleep(2)
                return True
            except Exception:
                return False
        except WebDriverException as e:
            logger.warning(f"页面加载失败 ({url}): {e}")
            return False

    def _validate_cookies(self, exam_url: str) -> bool:
        """使用已保存的 Cookie 访问目标 URL，判断是否会被重定向到登录页。"""
        driver = self.driver
        try:
            if not self._safe_get(exam_url):
                logger.warning("无法访问答题链接，尝试刷新...")
                try:
                    driver.refresh()
                    sleep(2)
                except Exception:
                    return False

            current_url = driver.current_url
            if self.cfg.LOGIN_DOMAIN_HINT in current_url:
                logger.info("Cookie 已失效或不存在，需要重新登录。")
                return False
            else:
                logger.info("Cookie 验证通过，可直接进入答题。")
                return True
        except Exception as e:
            logger.warning(f"Cookie 验证异常: {e}")
            return False

    # ---------- 终端显示二维码 ----------
    def _display_qr_in_terminal(self, qr_element) -> bool:
        """将浏览器中的二维码图片在终端中显示。"""
        try:
            from PIL import Image
            import sys

            img = self.solution.screenshot_web_element(qr_element)
            if img.size[0] == 0 or img.size[1] == 0:
                return False

            # 缩放到适合终端的宽度（每列2像素高，每个字符约1像素宽）
            max_w = 40
            ratio = max_w / img.size[0]
            new_w = max_w
            new_h = int(img.size[1] * ratio)
            # 确保高度为偶数（每2行合并为1个字符行）
            if new_h % 2 != 0:
                new_h += 1
            new_h = max(2, new_h)
            img = img.resize((new_w, new_h), Image.NEAREST)

            px = img.load()
            w, h = img.size

            sys.stdout.write("\n")
            for y in range(0, h, 2):
                line = ""
                for x in range(w):
                    r1, g1, b1 = px[x, y][:3]
                    r2, g2, b2 = px[x, y + 1][:3]
                    line += f"\033[48;2;{r1};{g1};{b1}m\033[38;2;{r2};{g2};{b2}m▀\033[0m"
                sys.stdout.write(line + "\n")
            sys.stdout.flush()
            return True
        except Exception as e:
            logger.error(f"终端显示二维码失败: {e}")
            return False

    # ---------- 登录（含终端二维码） ----------
    def _handle_login(
        self,
        exam_url: str,
        login_wait_seconds: int = 300
    ) -> bool:
        """
        完整登录流程：
        1. 用户输入链接
        2. 使用保存的凭据访问链接 → 判断是否需要登录
        3. 如需登录 → 在终端显示二维码 → 用户扫码
        4. 轮询检测前端 HTML 是否发生较大变化（变化率 > 40%）
        5. 检测到变动 → 保存新凭据 → 关闭旧浏览器 → 重新打开浏览器加载新凭据
        6. 使用新凭据打开用户输入的答题链接
        """
        driver = self.driver

        # 第一步：用已有 Cookie 尝试访问
        if self._validate_cookies(exam_url):
            return True

        # Cookie 无效，导航到登录页（driver 已在 _validate_cookies 中被重定向到登录页）
        sleep(2)
        current_url = driver.current_url

        if self.cfg.LOGIN_DOMAIN_HINT not in current_url:
            # 不在登录页但 _validate_cookies 返回 False，尝试直接导航到登录页
            try:
                self._safe_get(f"https://{self.cfg.LOGIN_QR_DOMAIN}")
            except Exception:
                pass

        # 第二步：获取并显示二维码
        logger.info("=" * 50)
        logger.info("需要登录，请扫描下方二维码：")
        logger.info("=" * 50)

        # 尝试点击"二维码登录"标签（部分页面默认显示密码登录）
        try:
            driver.execute_script("""
                var tabs = document.querySelectorAll('a, span, div, li, label');
                for (var i = 0; i < tabs.length; i++) {
                    var txt = (tabs[i].innerText || tabs[i].textContent || '').trim();
                    for (var k = 0; k < arguments.length; k++) {
                        if (txt.indexOf(arguments[k]) >= 0) {
                            if (tabs[i].offsetParent !== null) {
                                try { tabs[i].click(); } catch(e) {}
                                return;
                            }
                        }
                    }
                }
            """, *self.cfg.QR_LOGIN_TAB_KEYWORDS)
            sleep(2)
        except Exception:
            pass

        # 定位二维码图片元素
        qr_element = driver.execute_script("""
            // 策略1: 查找 img/canvas 标签中尺寸合适的元素
            var imgs = document.querySelectorAll('img, canvas');
            for (var i = 0; i < imgs.length; i++) {
                if (imgs[i].offsetParent !== null) {
                    var w = imgs[i].naturalWidth || imgs[i].width || imgs[i].getBoundingClientRect().width;
                    var h = imgs[i].naturalHeight || imgs[i].height || imgs[i].getBoundingClientRect().height;
                    if (w >= 80 && h >= 80 && w <= 500 && h <= 500) {
                        var rect = imgs[i].getBoundingClientRect();
                        if (rect.top >= 0 && rect.left >= 0) return imgs[i];
                    }
                }
            }
            // 策略2: 按 class / id 关键词查找
            var selectors = [
                '[class*="qr"] img', '[class*="qrcode"] img', '[class*="QR"]',
                '[id*="qr"] img', '[class*="scan"] img', '[class*="code"] img',
                '.qr-code', '.login-qr', '.login-code', '#qrcode',
                // 超星学习通
                '#login_qr img', '.wx_qrcode', '.login_qr', '#qr_login'
            ];
            for (var j = 0; j < selectors.length; j++) {
                try {
                    var el = document.querySelector(selectors[j]);
                    if (el && el.offsetParent !== null) return el;
                } catch(e) {}
            }
            // 策略3: 查找容器中的第一个合适图片
            var containers = document.querySelectorAll(
                '[class*="qr-box"], [class*="code-box"], [class*="login-box"], ' +
                '[class*="scan-box"], [class*="qrcode"], [class*="login-form"]'
            );
            for (var k = 0; k < containers.length; k++) {
                var containerImg = containers[k].querySelector('img, canvas');
                if (containerImg && containerImg.offsetParent !== null) return containerImg;
            }
            return null;
        """)

        if qr_element:
            displayed = self._display_qr_in_terminal(qr_element)
            if displayed:
                logger.info(f"请使用「{self.cfg.NAME}」APP 扫描上方二维码完成登录。")
            else:
                logger.warning("二维码显示失败，请在浏览器窗口中扫码登录。")
        else:
            logger.warning("未找到二维码图片，请在浏览器窗口中扫码登录。")

        logger.info("=" * 50)

        # 第三步：轮询检测前端 HTML 是否发生较大变化（用户扫码后页面结构会改变）
        logger.info("等待用户扫码登录...")
        try:
            initial_html = driver.execute_script(
                "return document.documentElement.outerHTML;"
            ) or ""
            initial_len = len(initial_html)
        except Exception:
            initial_html = ""
            initial_len = 0

        login_detected = False
        for _ in range(login_wait_seconds):
            sleep(1)
            try:
                current_html = driver.execute_script(
                    "return document.documentElement.outerHTML;"
                ) or ""
                current_len = len(current_html)

                # 计算 HTML 变化比例
                if initial_len > 0:
                    len_diff = abs(current_len - initial_len) / initial_len
                else:
                    len_diff = 1.0 if current_len > 0 else 0.0

                # 变化超过 40% 判定为页面大规模变动
                if len_diff > 0.4:
                    logger.info(f"检测到前端页面大规模变动（变化率 {len_diff:.0%}），登录成功。")
                    login_detected = True
                    break
            except Exception:
                # 浏览器可能正在跳转，忽略异常继续等待
                pass

        if not login_detected:
            logger.error(f"登录等待超时（{login_wait_seconds} 秒）。")
            return False
        logger.info("正在保存新的登录凭据...")
        self._save_cookies()
        logger.info("新登录凭据已保存。")

        # 等待页面稳定（扫码登录后可能需要几秒跳转）
        sleep(2)

        # 直接用当前浏览器导航到答题链接，不重建浏览器
        logger.info("正在导航到答题链接...")
        self._safe_get(exam_url)
        sleep(2)

        # 验证确实进入了答题页
        if self.cfg.LOGIN_DOMAIN_HINT in self.driver.current_url:
            # Cookie 可能还没生效，再试一次
            logger.warning("仍被重定向到登录页，尝试重新加载 Cookie 后重试...")
            self._reopen_browser()
            self._safe_get(exam_url)
            sleep(2)
            if self.cfg.LOGIN_DOMAIN_HINT in self.driver.current_url:
                logger.error("重新打开后仍被重定向到登录页，请重试。")
                return False

        logger.info("已成功进入答题界面。")
        return True

    def run_exam(self, exam_url: str):
        # 先输入链接，再启动浏览器
        self._ensure_browser()

        # 登录流程：验证Cookie → 终端显示二维码 → 保存凭据 → 重新打开浏览器 → 打开链接
        if not self._handle_login(exam_url):
            return

        # _handle_login 内部可能重建了浏览器，重新获取 driver 引用
        driver = self.driver

        # 等待页面完全加载
        sleep(3)

        # 处理"开始答题"入口按钮
        self._click_start_if_needed()
        sleep(3)

        # 再次等待，确保第一题完全加载（Vue 渲染需要时间）
        logger.info("等待第一题加载...")
        try:
            WebDriverWait(driver, 15, poll_frequency=0.5).until(
                lambda d: d.execute_script("""
                    // 学习通：div[role='radio'] 或 div[class*='answerBg']
                    var chaoxing = document.querySelectorAll("div[role='radio'], div[class*='answerBg']");
                    var vis = 0;
                    for (var i = 0; i < chaoxing.length; i++) {
                        if (chaoxing[i].offsetParent !== null) vis++;
                    }
                    if (vis >= 2) return true;

                    // 智慧树：el-radio / option-item
                    var opts = document.querySelectorAll('.el-radio, .option-item, [class*="option"], li[class*="option"]');
                    var vis2 = 0;
                    for (var j = 0; j < opts.length; j++) {
                        if (opts[j].offsetParent !== null) vis2++;
                    }
                    if (vis2 >= 2) return true;

                    // fallback: A/B/C/D 开头元素
                    var all = document.querySelectorAll('div, li, span, label');
                    var cnt = 0;
                    for (var a = 0; a < all.length; a++) {
                        var t = (all[a].innerText || all[a].textContent || '').trim();
                        if (/^[A-Z]\\s/.test(t) && all[a].offsetParent !== null) cnt++;
                    }
                    return cnt >= 2;
                """)
            )
            logger.info("第一题已加载。")
        except TimeoutException:
            logger.warning("等待第一题加载超时，尝试继续。")

        logger.info("开始答题流程...")

        # 学习通 tab 模式：先统计总题数，再点击第一题
        total_questions = 0
        if getattr(self.cfg, 'NAV_MODE', 'button') == 'tab':
            total_questions = self._count_total_questions()
            logger.info(f"检测到共 {total_questions} 道题目。")
            self._click_first_tab()
            sleep(2)
        else:
            total_questions = 200  # 智慧树用按钮翻题，设上限

        question_index = 0

        while question_index < total_questions:
            question_index += 1
            logger.info(f"========== 第 {question_index}/{total_questions} 题 ==========")

            # 等待当前题渲染完成
            self._wait_for_question_ready()
            sleep(0.5)

            # 最后一题页面不滚动，用视口底部 h3 识别
            is_last = (question_index >= total_questions)
            self.solution._use_last_h3 = is_last
            success = self._solve_current_question()
            if not success:
                logger.warning(f"第 {question_index} 题解答失败。")

            sleep(1)

            # 最后一题答完就结束
            if question_index >= total_questions:
                break

            # 翻到下一题
            if getattr(self.cfg, 'NAV_MODE', 'button') == 'tab':
                if self._goto_next_question_tab() is None:
                    break
            elif getattr(self.cfg, 'NAV_MODE', 'button') == 'scroll':
                if self._goto_next_question_scroll() is None:
                    break
            else:
                if self._go_next_question() is None:
                    break

            sleep(2)

        logger.info(f"答题流程结束，共处理 {question_index}/{total_questions} 题。答题完成！")
        print("\n" + "=" * 60)
        print("  答题已完成！请自行查看答题结果。")
        print("  确认无误后，请手动关闭浏览器窗口。")
        input("  关闭浏览器后，按回车继续... ")
        print("=" * 60)

        # 等用户关闭浏览器后，保存 Cookie 并清理
        try:
            self._save_cookies()
        except Exception:
            pass
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        self.driver = None

    # ---------- 点击"开始答题" ----------
    def _click_start_if_needed(self):
        driver = self.driver
        try:
            keywords_js = json.dumps(self.cfg.START_BTN_KEYWORDS)
            clicked = driver.execute_script(f"""
                function fireClick(el) {{
                    try {{ el.click(); }} catch(e) {{}}
                    try {{ el.dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true}})); }} catch(e) {{}}
                    try {{
                        var r = el.getBoundingClientRect();
                        var o = {{bubbles: true, cancelable: true, view: window,
                            clientX: r.left+r.width/2, clientY: r.top+r.height/2}};
                        el.dispatchEvent(new MouseEvent('mousedown', o));
                        el.dispatchEvent(new MouseEvent('mouseup', o));
                        el.dispatchEvent(new MouseEvent('click', o));
                    }} catch(e) {{}}
                }}
                var keywords = {keywords_js};
                var all = document.querySelectorAll('button, span, div, a');
                for (var i = 0; i < all.length; i++) {{
                    var txt = (all[i].innerText || all[i].textContent || '').trim();
                    for (var k = 0; k < keywords.length; k++) {{
                        if (txt === keywords[k] || txt.indexOf(keywords[k]) >= 0) {{
                            if (all[i].offsetParent !== null) {{
                                fireClick(all[i]);
                                return true;
                            }}
                        }}
                    }}
                }}
                // 尝试查找 el-button 元素
                var buttons = document.querySelectorAll('.el-button, button.el-button, [class*="start-btn"], [class*="begin-btn"]');
                for (var j = 0; j < buttons.length; j++) {{
                    var bt = (buttons[j].innerText || buttons[j].textContent || '').trim();
                    for (var k2 = 0; k2 < keywords.length; k2++) {{
                        if (bt === keywords[k2] || bt.indexOf(keywords[k2]) >= 0) {{
                            if (buttons[j].offsetParent !== null) {{
                                fireClick(buttons[j]);
                                return true;
                            }}
                        }}
                    }}
                }}
                return false;
            """)
            if clicked:
                logger.info(f"已点击「开始答题」按钮。")
            else:
                logger.debug("未找到「开始答题」按钮，可能已直接进入答题页。")
        except Exception as e:
            logger.debug(f"查找开始答题按钮异常: {e}")

    # ---------- 检测考试是否结束 ----------
    def _detect_exam_finished(self) -> bool:
        driver = self.driver
        try:
            keywords_js = json.dumps(self.cfg.EXAM_FINISHED_KEYWORDS)
            result = driver.execute_script(f"""
                var bodyText = (document.body.innerText || document.body.textContent || '');

                // 必须有明确的"提交/交卷成功"关键词
                var strongKeywords = {keywords_js};
                var hasFinishedText = false;
                for (var i = 0; i < strongKeywords.length; i++) {{
                    if (bodyText.indexOf(strongKeywords[i]) >= 0) {{
                        hasFinishedText = true;
                        break;
                    }}
                }}
                if (!hasFinishedText) return false;

                // 确认页面上没有题目元素（防止在答题页误判）
                var questionEls = document.querySelectorAll(
                    '[class*="question"], [class*="topic"], [class*="stem"],' +
                    'input[type="radio"], input[type="checkbox"],' +
                    '.option-item, [class*="option"]'
                );
                var hasQuestionVisible = false;
                for (var q = 0; q < questionEls.length; q++) {{
                    if (questionEls[q].offsetParent !== null) {{
                        hasQuestionVisible = true;
                        break;
                    }}
                }}
                // 有完成文本 且 无可见题目 → 确实完成了
                return hasFinishedText && !hasQuestionVisible;
            """)
            return bool(result)
        except Exception:
            return False

    # ---------- 解答当前题目 ----------
    def _solve_current_question(self) -> bool:
        driver = self.driver
        # 等待题目区域加载（最多 15 秒，适应慢网络）
        try:
            WebDriverWait(driver, 15, poll_frequency=0.5).until(
                lambda d: d.execute_script("""
                    // 清除残留标记
                    var old = document.querySelectorAll('[__opt_idx__]');
                    for (var oi = 0; oi < old.length; oi++) {
                        old[oi].removeAttribute('__opt_idx__');
                        old[oi].removeAttribute('__opt_text__');
                    }
                    // 策略1: 可见的 radio/checkbox input
                    var radios = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                    for (var i = 0; i < radios.length; i++) {
                        if (radios[i].offsetParent !== null) return true;
                    }
                    // 策略2: 常见选项类名
                    var optSelectors = [
                        '.el-radio', '.option-item', '[class*="option-item"]',
                        'li[class*="option"]', '.options li', '.options div',
                        '.option', '.choice-item', '[class*="choice"]',
                        '.answer-item', '[class*="answer-"]',
                        '.topic-option', '.exam-option', '[class*="exam-option"]',
                        'label.el-radio', '.radio-item', '.check-item',
                        '[class*="option-wrap"]', '[class*="option-box"]'
                    ];
                    for (var s = 0; s < optSelectors.length; s++) {
                        try {
                            var els = document.querySelectorAll(optSelectors[s]);
                            var vis = 0;
                            for (var e = 0; e < els.length; e++) {
                                if (els[e].offsetParent !== null) vis++;
                            }
                            if (vis >= 2) return true;
                        } catch(e) {}
                    }
                    // 策略3: 文本以 A/B/C/D 开头的可见元素（≥2个）
                    var allEls = document.querySelectorAll('div, li, span, label, p, dt, dd');
                    var optLike = 0;
                    for (var t = 0; t < allEls.length; t++) {
                        var txt = (allEls[t].innerText || allEls[t].textContent || '').trim();
                        if (/^[A-Z][.、)）\\s]/.test(txt) && txt.length > 2 && txt.length < 500 &&
                            allEls[t].offsetParent !== null) {
                            optLike++;
                        }
                    }
                    if (optLike >= 2) return true;
                    // 策略4: 题目容器元素有内容
                    var qSelectors = [
                        '.topic', '.subject', '.stem', '[class*="topic"]',
                        '[class*="subject"]', '[class*="stem"]',
                        '[class*="question"]', '[class*="exam"]',
                        '.ques-card-box', '.ques-item', '[class*="ques"]',
                        '.el-card__body', '.el-dialog__body'
                    ];
                    for (var q = 0; q < qSelectors.length; q++) {
                        try {
                            var qel = document.querySelector(qSelectors[q]);
                            if (qel && qel.offsetParent !== null &&
                                (qel.innerText || qel.textContent || '').trim().length > 10) {
                                return true;
                            }
                        } catch(e) {}
                    }
                    // 策略5: body 文本足够长（≥50字符）
                    var bodyText = (document.body.innerText || document.body.textContent || '').trim();
                    if (bodyText.length > 50) return true;
                    return false;
                """)
            )
        except TimeoutException:
            logger.error("等待题目区域超时。")
            return False
        except Exception as e:
            logger.error(f"等待题目区域异常: {e}")
            return False

        # 重试 3 次（Vue 渲染可能异步更新 DOM）
        for retry in range(3):
            try:
                if retry > 0:
                    logger.info(f"第 {retry + 1} 次重试解答...")
                    sleep(1.5)
                result = self.solution.solve_exam_question(driver, self.cfg.to_dict())
                if result:
                    return True
            except Exception as e:
                logger.error(f"解答当前题目异常 (尝试 {retry + 1}/3): {e}")
                import traceback
                logger.debug(traceback.format_exc())

        logger.error("3 次重试后仍无法解答当前题目。")
        return False

    # ---------- 下一题 ----------
    def _go_next_question(self) -> Optional[bool]:
        """
        点击"下一题"按钮。
        返回值:
            True  - 成功点击了"下一题"
            False - 已点击交卷按钮（最后一题）
            None  - 未找到"下一题"按钮也未找到交卷按钮，应停止答题
        """
        driver = self.driver
        try:
            # 序列化平台配置供 JS 使用
            next_kw = json.dumps(self.cfg.NEXT_BTN_KEYWORDS)
            sub_kw = json.dumps(self.cfg.SUBMIT_BTN_KEYWORDS)
            conf_kw = json.dumps(self.cfg.CONFIRM_BTN_KEYWORDS)
            known_sel = json.dumps(self.cfg.NEXT_BTN_KNOWN_CLASSES)

            # 检测是否最后一题（只有交卷按钮，没有下一题按钮）
            is_last = driver.execute_script(f"""
                if (document.body.getAttribute('__last_question__') === '1') return true;
                var nextKeywords = {next_kw};
                var submitKeywords = {sub_kw};
                var allBtns = document.querySelectorAll('button, span, div, a, li');
                var hasSubmit = false, hasNext = false;
                for (var i = 0; i < allBtns.length; i++) {{
                    var txt = (allBtns[i].innerText || allBtns[i].textContent || '').trim();
                    for (var s = 0; s < submitKeywords.length; s++) {{
                        if (txt === submitKeywords[s] || txt.indexOf(submitKeywords[s]) >= 0) {{
                            if (allBtns[i].offsetParent !== null) {{
                                hasSubmit = true;
                                break;
                            }}
                        }}
                    }}
                    for (var n = 0; n < nextKeywords.length; n++) {{
                        if (txt === nextKeywords[n] || txt.indexOf(nextKeywords[n]) >= 0) {{
                            if (allBtns[i].offsetParent !== null) {{
                                hasNext = true;
                                break;
                            }}
                        }}
                    }}
                    if (hasSubmit && hasNext) break;
                }}
                if (hasSubmit && !hasNext) {{
                    document.body.setAttribute('__last_question__', '1');
                    return true;
                }}
                return false;
            """)

            if is_last:
                logger.info("检测到最后一题，点击交卷/提交按钮...")
                clicked = driver.execute_script(f"""
                    function fireAll(el) {{
                        var r = el.getBoundingClientRect();
                        var cx = r.left + r.width / 2;
                        var cy = r.top + r.height / 2;
                        var o = {{bubbles: true, cancelable: true, view: window, clientX: cx, clientY: cy}};
                        try {{ el.dispatchEvent(new MouseEvent('mouseover', o)); }} catch(e) {{}}
                        try {{ el.dispatchEvent(new MouseEvent('mousedown', o)); }} catch(e) {{}}
                        try {{ el.dispatchEvent(new MouseEvent('mouseup', o)); }} catch(e) {{}}
                        try {{ el.click(); }} catch(e) {{}}
                        try {{ el.dispatchEvent(new MouseEvent('click', o)); }} catch(e) {{}}
                        try {{ el.dispatchEvent(new PointerEvent('click', o)); }} catch(e) {{}}
                    }}
                    var submitKeywords = {sub_kw};
                    var all = document.querySelectorAll('button, span, div, a');
                    for (var i = 0; i < all.length; i++) {{
                        var txt = (all[i].innerText || all[i].textContent || '').trim();
                        for (var s = 0; s < submitKeywords.length; s++) {{
                            if (txt === submitKeywords[s] || txt.indexOf(submitKeywords[s]) >= 0) {{
                                if (all[i].offsetParent !== null) {{
                                    fireAll(all[i]);
                                    return true;
                                }}
                            }}
                        }}
                    }}
                    return false;
                """)
                if clicked:
                    logger.info("已点击交卷按钮，检测确认弹窗...")
                    sleep(1.5)
                    driver.execute_script(f"""
                        var confirmKeywords = {conf_kw};
                        var all = document.querySelectorAll('button, span, div, a');
                        for (var i = 0; i < all.length; i++) {{
                            var txt = (all[i].innerText || all[i].textContent || '').trim();
                            for (var c = 0; c < confirmKeywords.length; c++) {{
                                if (txt === confirmKeywords[c] || txt.indexOf(confirmKeywords[c]) >= 0) {{
                                    if (all[i].offsetParent !== null) {{
                                        // 模拟真实鼠标事件
                                        var r = all[i].getBoundingClientRect();
                                        var cx = r.left + r.width / 2;
                                        var cy = r.top + r.height / 2;
                                        try {{ all[i].dispatchEvent(new MouseEvent('mouseover', {{bubbles: true, cancelable: true, view: window, clientX: cx, clientY: cy}})); }} catch(e) {{}}
                                        try {{ all[i].dispatchEvent(new MouseEvent('mousedown', {{bubbles: true, cancelable: true, view: window, clientX: cx, clientY: cy}})); }} catch(e) {{}}
                                        try {{ all[i].dispatchEvent(new MouseEvent('mouseup', {{bubbles: true, cancelable: true, view: window, clientX: cx, clientY: cy}})); }} catch(e) {{}}
                                        try {{ all[i].click(); }} catch(e) {{}}
                                        return true;
                                    }}
                                }}
                            }}
                        }}
                    """)
                    sleep(5)
                return False

            # 强力查找并点击"下一题"
            next_clicked = driver.execute_script(f"""
                function singleClick(el) {{
                    try {{ el.click(); }} catch(e) {{}}
                }}

                function isVisible(el) {{
                    if (!el) return false;
                    var rect = el.getBoundingClientRect();
                    return rect.width > 0 || rect.height > 0 || el.offsetParent !== null;
                }}

                var nextKeywords = {next_kw};
                var knownSelectors = {known_sel};

                // 策略0: 直接按平台已知类名查找（最可靠）
                for (var s = 0; s < knownSelectors.length; s++) {{
                    try {{
                        var els = document.querySelectorAll(knownSelectors[s]);
                        for (var k = 0; k < els.length; k++) {{
                            var t = (els[k].innerText || els[k].textContent || '').trim();
                            for (var n = 0; n < nextKeywords.length; n++) {{
                                if ((t === nextKeywords[n] || t.indexOf(nextKeywords[n]) >= 0) && isVisible(els[k])) {{
                                    singleClick(els[k]);
                                    return 'known:' + knownSelectors[s];
                                }}
                            }}
                        }}
                    }} catch(e) {{}}
                }}

                // 策略1: 文本精确查找
                var all = document.querySelectorAll('button, a, span, div, li');
                for (var i = 0; i < all.length; i++) {{
                    var txt = (all[i].innerText || all[i].textContent || '').trim();
                    for (var n = 0; n < nextKeywords.length; n++) {{
                        if (txt === nextKeywords[n] || txt.indexOf(nextKeywords[n]) >= 0) {{
                            if (isVisible(all[i])) {{
                                singleClick(all[i]);
                                return 'text';
                            }}
                        }}
                    }}
                }}

                // 策略2: CSS选择器查找
                var selectors2 = [
                    '[class*="next-btn"]', '[class*="nextBtn"]',
                    '.el-button--primary', 'button.el-button--primary',
                    '[class*="footer"] button', '[class*="footer"] span',
                    '[class*="bottom"] span', '[class*="action"] span',
                    '[class*="stui__nav"]', '[class*="pagination"]'
                ];
                for (var j = 0; j < selectors2.length; j++) {{
                    try {{
                        var els2 = document.querySelectorAll(selectors2[j]);
                        for (var k2 = 0; k2 < els2.length; k2++) {{
                            var t2 = (els2[k2].innerText || els2[k2].textContent || '').trim();
                            for (var n2 = 0; n2 < nextKeywords.length; n2++) {{
                                if ((t2 === nextKeywords[n2] || t2.indexOf(nextKeywords[n2]) >= 0) && isVisible(els2[k2])) {{
                                    singleClick(els2[k2]);
                                    return 'selector:' + selectors2[j];
                                }}
                            }}
                        }}
                    }} catch(e) {{}}
                }}

                // 策略3: 查找页面底部按钮区域
                var footerAreas = document.querySelectorAll('[class*="footer"], [class*="bottom"], [class*="action"], [class*="operation"], [class*="btn"], [class*="nav"], [class*="pager"]');
                for (var f = 0; f < footerAreas.length; f++) {{
                    if (!isVisible(footerAreas[f])) continue;
                    var btns = footerAreas[f].querySelectorAll('button, span, div, a');
                    for (var b = 0; b < btns.length; b++) {{
                        var bt = (btns[b].innerText || btns[b].textContent || '').trim();
                        for (var n3 = 0; n3 < nextKeywords.length; n3++) {{
                            if (bt === nextKeywords[n3] || bt.indexOf(nextKeywords[n3]) >= 0) {{
                                singleClick(btns[b]);
                                return 'footer';
                            }}
                        }}
                    }}
                }}

                return false;
            """)

            if next_clicked:
                logger.info(f"已触发下一题按钮({next_clicked})，等待页面切换...")
                sleep(0.3)
                # 清除旧标记
                driver.execute_script("""
                    var old = document.querySelectorAll('[__opt_idx__]');
                    for (var oi = 0; oi < old.length; oi++) {
                        old[oi].removeAttribute('__opt_idx__');
                        old[oi].removeAttribute('__opt_text__');
                    }
                """)
                return True
            else:
                # 未找到"下一题"按钮，检查是否有交卷按钮
                has_submit = driver.execute_script(f"""
                    var submitKeywords = {sub_kw};
                    var all = document.querySelectorAll('button, span, div, a');
                    for (var i = 0; i < all.length; i++) {{
                        var txt = (all[i].innerText || all[i].textContent || '').trim();
                        for (var s = 0; s < submitKeywords.length; s++) {{
                            if (txt === submitKeywords[s] || txt.indexOf(submitKeywords[s]) >= 0) {{
                                if (all[i].offsetParent !== null) {{
                                    try {{ all[i].click(); }} catch(e) {{
                                        var r = all[i].getBoundingClientRect();
                                        all[i].dispatchEvent(new MouseEvent('click',
                                            {{bubbles: true, clientX: r.left+r.width/2, clientY: r.top+r.height/2}}));
                                    }}
                                    return true;
                                }}
                            }}
                        }}
                    }}
                    return false;
                """)
                if has_submit:
                    logger.info("已点击交卷按钮作为兜底。")
                    sleep(5)
                    return False
                # 既没有"下一题"也没有"交卷" → 停止答题
                logger.warning("页面上未找到「下一题」按钮，答题可能已结束或页面异常。")
                return None
        except Exception as e:
            logger.error(f"点击下一题失败: {e}")
            return None

    # ---------- 统计总题数 ----------
    def _count_total_questions(self) -> int:
        """统计所有 ul.topicNumber_list 下 li 的数量。"""
        driver = self.driver
        try:
            total = driver.execute_script("""
                var lists = document.querySelectorAll('ul.topicNumber_list');
                var count = 0;
                for (var i = 0; i < lists.length; i++) {
                    count += lists[i].querySelectorAll('li').length;
                }
                return count;
            """)
            return total or 200
        except Exception:
            return 200

    # ---------- 点击第一题（学习通 tab 模式）----------
    def _click_first_tab(self):
        """页面加载后第一题可能没选中，点击题号列表第一个 li。"""
        driver = self.driver
        try:
            driver.execute_script("""
                function fireClick(el) {
                    var r = el.getBoundingClientRect();
                    var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
                    var o = {bubbles: true, cancelable: true, view: window, clientX: cx, clientY: cy};
                    try { el.dispatchEvent(new MouseEvent('mouseover', o)); } catch(e) {}
                    try { el.dispatchEvent(new MouseEvent('mousedown', o)); } catch(e) {}
                    try { el.dispatchEvent(new MouseEvent('mouseup', o)); } catch(e) {}
                    try { el.click(); } catch(e) {}
                    try { el.dispatchEvent(new MouseEvent('click', o)); } catch(e) {}
                }
                var list = document.querySelector('ul.topicNumber_list');
                if (!list) return;
                var items = list.querySelectorAll('li');
                if (items.length === 0) return;
                fireClick(items[0]);
                return;
            """)
            logger.info("已点击第一题题号，滚动到视口。")
            driver.execute_script(r"""
                var h3s = document.querySelectorAll('h3.mark_name, h3[class*="mark_name"]');
                for (var i = 0; i < h3s.length; i++) {
                    var r = h3s[i].getBoundingClientRect();
                    if (r.top >= -10 && r.top < window.innerHeight * 0.7 && h3s[i].offsetParent !== null) {
                        h3s[i].scrollIntoView({block: 'start', inline: 'nearest', behavior: 'instant'});
                        window.scrollBy(0, -40);
                        break;
                    }
                }
            """)
        except Exception as e:
            logger.debug(f"点击第一题失败: {e}")

    # ---------- 等待当前题渲染 ----------
    def _wait_for_question_ready(self, timeout: int = 10):
        """等待视口内出现有内容的 h3 + 选项。"""
        driver = self.driver
        try:
            WebDriverWait(driver, timeout, poll_frequency=0.5).until(
                lambda d: d.execute_script(r"""
                    var vh = window.innerHeight;
                    var h3s = document.querySelectorAll('h3.mark_name, h3[class*="mark_name"]');
                    for (var i = 0; i < h3s.length; i++) {
                        var r = h3s[i].getBoundingClientRect();
                        if (r.top >= -10 && r.top < vh && h3s[i].offsetParent !== null) {
                            var txt = (h3s[i].innerText || h3s[i].textContent || '').trim();
                            if (txt.length > 10) {
                                // 再检查后面有 stem_answer 且含选项
                                var next = h3s[i].nextElementSibling;
                                while (next) {
                                    if (next.classList && next.classList.contains('stem_answer')) {
                                        var opts = next.querySelectorAll("div[role='radio'], div[role='checkbox']");
                                        for (var o = 0; o < opts.length; o++) {
                                            if (opts[o].offsetParent !== null) return true;
                                        }
                                    }
                                    next = next.nextElementSibling;
                                }
                            }
                        }
                    }
                    return false;
                """)
            )
            logger.debug("当前题已渲染就绪。")
        except TimeoutException:
            logger.warning("等待当前题渲染超时，尝试继续。")

    # ---------- 滚动翻题（学习通模式）----------
    def _goto_next_question_scroll(self) -> Optional[bool]:
        """
        学习通页面题目是滚动加载的，不是按钮翻题。
        滚动到当前可见选项区域之后，检查是否有新题目出现。
        返回值:
            True  - 成功滚动到下一题
            False - 已到最后一题（找到交卷按钮）
            None  - 无法继续，停止答题
        """
        driver = self.driver
        try:
            # 先检查是否有提交按钮（说明可能是最后一题或页面结束了）
            sub_kw = json.dumps(self.cfg.SUBMIT_BTN_KEYWORDS)
            has_submit = driver.execute_script(f"""
                var submitKeywords = {sub_kw};
                var all = document.querySelectorAll('button, span, div, a');
                for (var i = 0; i < all.length; i++) {{
                    var txt = (all[i].innerText || all[i].textContent || '').trim();
                    for (var s = 0; s < submitKeywords.length; s++) {{
                        if (txt.indexOf(submitKeywords[s]) >= 0) {{
                            if (all[i].offsetParent !== null) {{
                                return true;
                            }}
                        }}
                    }}
                }}
                return false;
            """)

            # 检查考试结束
            if self._detect_exam_finished():
                logger.info("考试已完成。")
                return False

            # 获取当前所有题目的数量（作为滚动前后的对比基准）
            prev_count = driver.execute_script("""
                var opts = document.querySelectorAll('.g-checkbox, .ckeCK, .stui__radio, .stui__checkbox, ' +
                    'input[type="radio"], input[type="checkbox"]');
                var vis = 0;
                for (var o = 0; o < opts.length; o++) {
                    if (opts[o].offsetParent !== null) vis++;
                }
                return vis;
            """)

            # 使用 window.scrollBy 向下滚动一屏
            driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8);")
            sleep(1.5)

            # 验证新题目是否出现（选项数量变化或新选项出现）
            new_count = driver.execute_script("""
                var opts = document.querySelectorAll('.g-checkbox, .ckeCK, .stui__radio, .stui__checkbox, ' +
                    'input[type="radio"], input[type="checkbox"]');
                var vis = 0;
                for (var o = 0; o < opts.length; o++) {
                    if (opts[o].offsetParent !== null) vis++;
                }
                return vis;
            """)

            if new_count > prev_count:
                logger.info(f"滚动到下一题（选项数 {prev_count} -> {new_count}），等待页面渲染...")
                sleep(1)
                return True
            elif new_count == prev_count and new_count > 0:
                # 可能同一题有多组选项，或者滚动到了同一题的更多选项
                logger.info("滚动后选项数不变，可能仍在当前题或已到末尾。")
                if has_submit:
                    logger.info("检测到提交按钮，可能已是最后一题。")
                    # 点击提交
                    driver.execute_script(f"""
                        var submitKeywords = {sub_kw};
                        var all = document.querySelectorAll('button, span, div, a');
                        for (var i = 0; i < all.length; i++) {{
                            var txt = (all[i].innerText || all[i].textContent || '').trim();
                            for (var s = 0; s < submitKeywords.length; s++) {{
                                if (txt.indexOf(submitKeywords[s]) >= 0) {{
                                    if (all[i].offsetParent !== null) {{
                                        try {{ all[i].click(); }} catch(e) {{}}
                                        return;
                                    }}
                                }}
                            }}
                        }}
                    """)
                    sleep(3)
                    return False
                return True
            else:
                # 没有选项了，可能是最后一题
                if has_submit:
                    logger.info("已到题目末尾，点击提交按钮...")
                    driver.execute_script(f"""
                        var submitKeywords = {sub_kw};
                        var all = document.querySelectorAll('button, span, div, a');
                        for (var i = 0; i < all.length; i++) {{
                            var txt = (all[i].innerText || all[i].textContent || '').trim();
                            for (var s = 0; s < submitKeywords.length; s++) {{
                                if (txt.indexOf(submitKeywords[s]) >= 0) {{
                                    if (all[i].offsetParent !== null) {{
                                        try {{ all[i].click(); }} catch(e) {{}}
                                        return;
                                    }}
                                }}
                            }}
                        }}
                    """)
                    sleep(3)
                    return False
                logger.warning("未找到可滚动的新题目，停止答题。")
                return None
        except Exception as e:
            logger.error(f"滚动翻题失败: {e}")
            return None

    # ---------- 题号列表翻题（学习通 tab 模式）----------
    def _goto_next_question_tab(self) -> Optional[bool]:
        """
        点击当前题号的下一个 li 切换题目。
        返回值: True=已切换, None=无法继续
        """
        driver = self.driver
        try:
            clicked = driver.execute_script(f"""
                function fireClick(el) {{
                    var r = el.getBoundingClientRect();
                    var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
                    var o = {{bubbles: true, cancelable: true, view: window, clientX: cx, clientY: cy}};
                    try {{ el.dispatchEvent(new MouseEvent('mouseover', o)); }} catch(e) {{}}
                    try {{ el.dispatchEvent(new MouseEvent('mousedown', o)); }} catch(e) {{}}
                    try {{ el.dispatchEvent(new MouseEvent('mouseup', o)); }} catch(e) {{}}
                    try {{ el.click(); }} catch(e) {{}}
                    try {{ el.dispatchEvent(new MouseEvent('click', o)); }} catch(e) {{}}
                }}

                var allLists = document.querySelectorAll('ul.topicNumber_list');
                if (!allLists || allLists.length === 0) return 'no_list';

                var foundListIdx = -1, foundLiIdx = -1;
                for (var li = 0; li < allLists.length; li++) {{
                    var items = allLists[li].querySelectorAll('li');
                    for (var ii = 0; ii < items.length; ii++) {{
                        if (items[ii].className && items[ii].className.indexOf('current') >= 0) {{
                            foundListIdx = li; foundLiIdx = ii; break;
                        }}
                    }}
                    if (foundListIdx >= 0) break;
                }}

                if (foundListIdx < 0) {{
                    var firstItems = allLists[0].querySelectorAll('li');
                    if (firstItems.length > 0) {{ fireClick(firstItems[0]); return 'ok'; }}
                    return 'no_current';
                }}

                var curList = allLists[foundListIdx];
                var curItems = curList.querySelectorAll('li');

                if (foundLiIdx + 1 < curItems.length) {{
                    fireClick(curItems[foundLiIdx + 1]); return 'ok';
                }}

                // 跨列表
                if (foundListIdx + 1 < allLists.length) {{
                    var nextItems = allLists[foundListIdx + 1].querySelectorAll('li');
                    if (nextItems.length > 0) {{ fireClick(nextItems[0]); return 'ok'; }}
                }}

                return 'last';
            """)

            if clicked in ('no_list', 'no_current'):
                logger.warning("未找到题号列表。")
                return None

            logger.info(f"已切换到下一题 ({clicked})，等待渲染...")
            sleep(2)
            return True
        except Exception as e:
            logger.error(f"题号翻题失败: {e}")
            return None

    # ---------- 关闭 ----------
    def shutdown(self):
        if self._shutdown_done:
            return
        self._shutdown_done = True
        try:
            logger.info("触发服务关闭：准备先保存 Cookie")
            if self.driver is not None:
                self._save_cookies(self.cookies_file)
        except Exception as e:
            logger.warning(f"服务关闭保存 Cookie 失败：{e}")
        finally:
            try:
                if self.driver is not None:
                    self.driver.quit()
                    logger.info("浏览器已关闭，退出程序。")
            except Exception:
                pass
