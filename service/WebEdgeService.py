import json
from pathlib import Path
from typing import Optional
from time import sleep
from loguru import logger
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

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
"欸嘿嘿，一注释又少"
"二屎山又多"
"你看得下得去你就看吧！"
"一看一个不知声！过几天我自己都看不懂！"
"又不是造飞机大炮，差不多能跑就行啦"


class WebEdgeService:
    def __init__(
        self,
        configurator: Optional[WebDriverConfigurator] = None,
        cookies_file: Optional[str] = None
    ):
        self._shutdown_done = False
        self.cookies_file = cookies_file or resolve_cookie_file_path()
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

        self.configurator = configurator or WebDriverConfigurator(cookies_file=cookies_cfg_path)
        self.driver = self.configurator.build()
        self.solution = SolutionService()

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

    # ---------- 登录 ----------
    def _handle_login(
        self,
        login_domain_hint: str = "passport.zhihuishu.com",
        login_wait_seconds: int = 300
    ) -> bool:
        """检测当前页面是否需要登录，若是则等待用户完成登录并保存 Cookie。"""
        driver = self.driver
        sleep(2)
        current_url = driver.current_url
        if login_domain_hint in current_url:
            logger.warning("检测到未登录，请在浏览器窗口内完成登录（扫码或知到APP）。")
            try:
                WebDriverWait(driver, login_wait_seconds, poll_frequency=1).until(
                    lambda d: login_domain_hint not in d.current_url
                )
                logger.info("登录成功。")
                self._save_cookies()
                return True
            except TimeoutException:
                logger.error(f"登录等待超时（{login_wait_seconds} 秒）。")
                return False
        else:
            logger.info("已登录，继续。")
            return True

    def run_exam(self, exam_url: str):
        driver = self.driver
        driver.get(exam_url)
        logger.info(f"已打开答题网址: {exam_url}")

        if not self._handle_login():
            return

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
                    var inputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                    for (var i = 0; i < inputs.length; i++) {
                        if (inputs[i].offsetParent !== null) return true;
                    }
                    var opts = document.querySelectorAll('.el-radio, .option-item, [class*="option"], li[class*="option"]');
                    var vis = 0;
                    for (var j = 0; j < opts.length; j++) {
                        if (opts[j].offsetParent !== null) vis++;
                    }
                    if (vis >= 2) return true;
                    var all = document.querySelectorAll('div, li, span, label');
                    var cnt = 0;
                    for (var a = 0; a < all.length; a++) {
                        var t = (all[a].innerText || all[a].textContent || '').trim();
                        if (/^[A-Z][.、)）]/.test(t) && all[a].offsetParent !== null) cnt++;
                    }
                    return cnt >= 2;
                """)
            )
            logger.info("第一题已加载。")
        except TimeoutException:
            logger.warning("等待第一题加载超时，尝试继续。")

        logger.info("开始答题流程...")

        question_index = 0
        max_questions = 200

        while question_index < max_questions:
            question_index += 1
            logger.info(f"========== 第 {question_index} 题 ==========")

            # 记录答题前的页面指纹（跳过页面元数据，取题目内容区域）
            pre_solve_fingerprint = driver.execute_script("""
                var body = (document.body.innerText || document.body.textContent || '');
                // 跳过固定元数据，从第 100 字符开始取 300 字（含题干+选项）
                return body.substring(100, 400);
            """) or ""

            success = self._solve_current_question()
            if not success:
                logger.warning(f"第 {question_index} 题解答失败，尝试跳过。")
                driver.execute_script("""
                    var inputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                    if (inputs.length > 0) {
                        var vis = [];
                        for (var i = 0; i < inputs.length; i++) {
                            if (inputs[i].offsetParent !== null) vis.push(inputs[i]);
                        }
                        if (vis.length > 0) {
                            try { vis[0].click(); } catch(e) {}
                            try { vis[0].dispatchEvent(new Event('change', {bubbles: true})); } catch(e) {}
                        }
                    }
                """)
                sleep(0.5)

            # 检测选项点击后页面是否已自动跳转到下一题
            post_solve_fingerprint = driver.execute_script("""
                var body = (document.body.innerText || document.body.textContent || '');
                return body.substring(100, 400);
            """) or ""

            if pre_solve_fingerprint and post_solve_fingerprint and pre_solve_fingerprint != post_solve_fingerprint:
                logger.info("选项点击后页面已自动跳转到下一题，跳过「下一题」按钮。")
                logger.debug(f"指纹变化: {pre_solve_fingerprint[:80]}... → {post_solve_fingerprint[:80]}...")
                sleep(1)
                if self._detect_exam_finished():
                    logger.info("检测到考试已完成。")
                    break
                continue

            # 下一题/交卷
            if not self._go_next_question():
                sleep(2)
                if self._detect_exam_finished():
                    logger.info("已交卷，考试完成。")
                else:
                    logger.warning("无法继续答题且未检测到完成状态，手动停止。")
                break

            sleep(2)

            # 检测完成
            if self._detect_exam_finished():
                logger.info("检测到考试已完成。")
                break

        logger.info(f"答题流程结束，共处理 {question_index} 题。")

    # ---------- 点击"开始答题" ----------
    def _click_start_if_needed(self):
        driver = self.driver
        try:
            clicked = driver.execute_script("""
                function fireClick(el) {
                    try { el.click(); } catch(e) {}
                    try { el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true})); } catch(e) {}
                    try {
                        var r = el.getBoundingClientRect();
                        var o = {bubbles: true, cancelable: true, view: window,
                            clientX: r.left+r.width/2, clientY: r.top+r.height/2};
                        el.dispatchEvent(new MouseEvent('mousedown', o));
                        el.dispatchEvent(new MouseEvent('mouseup', o));
                        el.dispatchEvent(new MouseEvent('click', o));
                    } catch(e) {}
                }
                var keywords = ['开始答题', '开始考试', '进入考试', '开始作答', '进入答题'];
                var all = document.querySelectorAll('button, span, div, a');
                for (var i = 0; i < all.length; i++) {
                    var txt = (all[i].innerText || all[i].textContent || '').trim();
                    for (var k = 0; k < keywords.length; k++) {
                        if (txt === keywords[k] || txt.indexOf(keywords[k]) >= 0) {
                            if (all[i].offsetParent !== null) {
                                fireClick(all[i]);
                                return true;
                            }
                        }
                    }
                }
                // 尝试查找 el-button 元素
                var buttons = document.querySelectorAll('.el-button, button.el-button, [class*="start-btn"], [class*="begin-btn"]');
                for (var j = 0; j < buttons.length; j++) {
                    var bt = (buttons[j].innerText || buttons[j].textContent || '').trim();
                    for (var k2 = 0; k2 < keywords.length; k2++) {
                        if (bt === keywords[k2] || bt.indexOf(keywords[k2]) >= 0) {
                            if (buttons[j].offsetParent !== null) {
                                fireClick(buttons[j]);
                                return true;
                            }
                        }
                    }
                }
                return false;
            """)
            if clicked:
                logger.info("已点击「开始答题」按钮。")
            else:
                logger.debug("未找到「开始答题」按钮，可能已直接进入答题页。")
        except Exception as e:
            logger.debug(f"查找开始答题按钮异常: {e}")

    # ---------- 检测考试是否结束 ----------
    def _detect_exam_finished(self) -> bool:
        driver = self.driver
        try:
            result = driver.execute_script("""
                var bodyText = (document.body.innerText || document.body.textContent || '');

                // 必须有明确的"提交/交卷成功"关键词（弱关键词如"成绩""得分"不单独触发）
                var strongKeywords = ['提交成功', '交卷成功', '考试结束', '答题完成',
                    '试卷已提交', '已提交', '交卷完成', '恭喜您完成',
                    '不能继续答题', '无需再次答题', '您已完成'];
                var hasFinishedText = false;
                for (var i = 0; i < strongKeywords.length; i++) {
                    if (bodyText.indexOf(strongKeywords[i]) >= 0) {
                        hasFinishedText = true;
                        break;
                    }
                }
                if (!hasFinishedText) return false;

                // 确认页面上没有题目元素（防止在答题页误判）
                var questionEls = document.querySelectorAll(
                    '[class*="question"], [class*="topic"], [class*="stem"],' +
                    'input[type="radio"], input[type="checkbox"],' +
                    '.option-item, [class*="option"]'
                );
                var hasQuestionVisible = false;
                for (var q = 0; q < questionEls.length; q++) {
                    if (questionEls[q].offsetParent !== null) {
                        hasQuestionVisible = true;
                        break;
                    }
                }
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
                result = self.solution.solve_exam_question(driver)
                if result:
                    return True
            except Exception as e:
                logger.error(f"解答当前题目异常 (尝试 {retry + 1}/3): {e}")
                import traceback
                logger.debug(traceback.format_exc())

        logger.error("3 次重试后仍无法解答当前题目。")
        return False

    # ---------- 下一题 ----------
    def _go_next_question(self) -> bool:
        driver = self.driver
        try:
            # 检测是否最后一题（只有交卷按钮，没有下一题按钮）
            is_last = driver.execute_script("""
                if (document.body.getAttribute('__last_question__') === '1') return true;
                var allBtns = document.querySelectorAll('button, span, div, a, li');
                var hasSubmit = false, hasNext = false;
                for (var i = 0; i < allBtns.length; i++) {
                    var txt = (allBtns[i].innerText || allBtns[i].textContent || '').trim();
                    if ((txt === '交卷' || txt === '提交试卷' || txt === '提交') && allBtns[i].offsetParent !== null) {
                        hasSubmit = true;
                    }
                    if ((txt === '下一题' || txt.indexOf('下一题') >= 0) && allBtns[i].offsetParent !== null) {
                        hasNext = true;
                    }
                }
                if (hasSubmit && !hasNext) {
                    document.body.setAttribute('__last_question__', '1');
                    return true;
                }
                return false;
            """)

            if is_last:
                logger.info("检测到最后一题，点击交卷/提交按钮...")
                clicked = driver.execute_script("""
                    function fireAll(el) {
                        var r = el.getBoundingClientRect();
                        var o = {bubbles: true, cancelable: true, view: window,
                            clientX: r.left+r.width/2, clientY: r.top+r.height/2};
                        try { el.click(); } catch(e) {}
                        try { el.dispatchEvent(new MouseEvent('click', o)); } catch(e) {}
                        try { el.dispatchEvent(new PointerEvent('click', o)); } catch(e) {}
                    }
                    var all = document.querySelectorAll('button, span, div, a');
                    for (var i = 0; i < all.length; i++) {
                        var txt = (all[i].innerText || all[i].textContent || '').trim();
                        if (txt === '交卷' || txt === '提交试卷' || txt === '提交') {
                            if (all[i].offsetParent !== null) {
                                fireAll(all[i]);
                                return true;
                            }
                        }
                    }
                    return false;
                """)
                if clicked:
                    logger.info("已点击交卷按钮，检测确认弹窗...")
                    sleep(1.5)
                    driver.execute_script("""
                        var all = document.querySelectorAll('button, span, div, a');
                        for (var i = 0; i < all.length; i++) {
                            var txt = (all[i].innerText || all[i].textContent || '').trim();
                            if (txt === '确定' || txt === '确认' || txt === '是' || txt.indexOf('确定') >= 0) {
                                if (all[i].offsetParent !== null) {
                                    try { all[i].click(); } catch(e) {}
                                    return true;
                                }
                            }
                        }
                    """)
                    sleep(5)
                return False

            # 记录点击前的页面文本指纹（跳过元数据区域）
            pre_fingerprint = driver.execute_script("""
                var body = (document.body.innerText || document.body.textContent || '');
                return body.substring(100, 400);
            """) or ""

            # 强力查找并点击"下一题"（只触发一次点击，避免 Vue 收到多次事件导致跳题）
            next_clicked = driver.execute_script("""
                function singleClick(el) {
                    // 只使用一种点击方式，防止 Vue/Element 响应多次
                    try { el.click(); } catch(e) {}
                }

                function walkToBtn(el) {
                    var cur = el;
                    for (var up = 0; up < 6; up++) {
                        var tag = (cur.tagName || '').toLowerCase();
                        if (tag === 'button' || tag === 'a') return cur;
                        var cls = (cur.className || '').toString();
                        if (cls.indexOf('btn') >= 0 || cls.indexOf('button') >= 0) return cur;
                        if (cur.parentElement && cur.parentElement !== document.body) cur = cur.parentElement;
                        else break;
                    }
                    return el;
                }

                // 策略1: 文本精确查找 "下一题"（优先找 button 元素）
                var all = document.querySelectorAll('button, a, span, div, li');
                for (var i = 0; i < all.length; i++) {
                    var txt = (all[i].innerText || all[i].textContent || '').trim();
                    if (txt === '下一题' || txt === '下一頁') {
                        if (all[i].offsetParent !== null && all[i].offsetParent.offsetParent !== null) {
                            singleClick(walkToBtn(all[i]));
                            return true;
                        }
                    }
                }

                // 策略2: CSS选择器查找
                var selectors = [
                    '.next-btn', '.nextBtn', '.next-question', '[class*="next-btn"]', '[class*="nextBtn"]',
                    '.el-button--primary', 'button.el-button--primary',
                    '.submit-footer .next', '.question-footer .next',
                    '[class*="footer"] button', '[class*="footer"] span'
                ];
                for (var j = 0; j < selectors.length; j++) {
                    try {
                        var els = document.querySelectorAll(selectors[j]);
                        for (var k = 0; k < els.length; k++) {
                            var t = (els[k].innerText || els[k].textContent || '').trim();
                            if ((t === '下一题' || t.indexOf('下一题') >= 0) && els[k].offsetParent !== null) {
                                singleClick(els[k]);
                                return true;
                            }
                        }
                    } catch(e) {}
                }

                // 策略3: 查找页面底部按钮区域
                var footerAreas = document.querySelectorAll('[class*="footer"], [class*="bottom"], [class*="action"], [class*="operation"]');
                for (var f = 0; f < footerAreas.length; f++) {
                    if (footerAreas[f].offsetParent === null) continue;
                    var btns = footerAreas[f].querySelectorAll('button, span, div, a');
                    for (var b = 0; b < btns.length; b++) {
                        var bt = (btns[b].innerText || btns[b].textContent || '').trim();
                        if (bt === '下一题' || bt.indexOf('下一题') >= 0) {
                            singleClick(btns[b]);
                            return true;
                        }
                    }
                }

                return false;
            """)

            if next_clicked:
                logger.info("已触发下一题按钮，等待页面切换...")
                # 初始化页面指纹（记录点击前的 body 文本）
                driver.execute_script("""
                    var body = (document.body.innerText || document.body.textContent || '');
                    document.body.setAttribute('__prev_body__', body.substring(100, 400));
                """)
                sleep(0.3)
                # 清除旧标记
                driver.execute_script("""
                    var old = document.querySelectorAll('[__opt_idx__]');
                    for (var oi = 0; oi < old.length; oi++) {
                        old[oi].removeAttribute('__opt_idx__');
                        old[oi].removeAttribute('__opt_text__');
                    }
                """)
                # 检查页面指纹是否变化
                post_fingerprint = driver.execute_script("""
                    var body = (document.body.innerText || document.body.textContent || '');
                    return body.substring(100, 400);
                """) or ""
                pre_fingerprint = driver.execute_script(
                    "return document.body.getAttribute('__prev_body__') || '';"
                ) or ""
                if pre_fingerprint and post_fingerprint and pre_fingerprint != post_fingerprint:
                    logger.info("页面指纹已变化，视为切换成功。")
                else:
                    logger.warning("页面指纹未变化，尝试再次点击...")
                    driver.execute_script("""
                        var all = document.querySelectorAll('button, span, div, a');
                        for (var i = 0; i < all.length; i++) {
                            var txt = (all[i].innerText || all[i].textContent || '').trim();
                            if (txt === '下一题' && all[i].offsetParent !== null) {
                                try { all[i].click(); } catch(e) {}
                                return;
                            }
                        }
                    """)
                    sleep(0.5)
                return True
            else:
                logger.warning("未找到下一题按钮，尝试查找交卷按钮...")
                has_submit = driver.execute_script("""
                    var all = document.querySelectorAll('button, span, div, a');
                    for (var i = 0; i < all.length; i++) {
                        var txt = (all[i].innerText || all[i].textContent || '').trim();
                        if ((txt === '交卷' || txt === '提交试卷' || txt === '提交') &&
                            all[i].offsetParent !== null) {
                            try { all[i].click(); } catch(e) {
                                var r = all[i].getBoundingClientRect();
                                all[i].dispatchEvent(new MouseEvent('click',
                                    {bubbles: true, clientX: r.left+r.width/2, clientY: r.top+r.height/2}));
                            }
                            return true;
                        }
                    }
                    return false;
                """)
                if has_submit:
                    logger.info("已点击交卷按钮作为兜底。")
                    sleep(5)
                return False
        except Exception as e:
            logger.error(f"点击下一题失败: {e}")
            return False

    # ---------- 关闭 ----------
    def shutdown(self):
        if self._shutdown_done:
            return
        self._shutdown_done = True
        try:
            logger.info("触发服务关闭：准备先保存 Cookie")
            self._save_cookies(self.cookies_file)
        except Exception as e:
            logger.warning(f"服务关闭保存 Cookie 失败：{e}")
        finally:
            try:
                self.driver.quit()
                logger.info("浏览器已关闭，退出程序。")
            except Exception:
                pass
