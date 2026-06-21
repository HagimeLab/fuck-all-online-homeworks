import numpy as np
import tempfile
import os
import json

from typing import List, Any, Optional, Dict
from PIL import Image
from loguru import logger
from cnocr import CnOcr
from tools.llms.DeepSeek import DeepSeek, get_client
from io import BytesIO
from time import sleep


class SolutionService:
    def __init__(self, llm: Optional[DeepSeek] = None, platform: str = "zhihuishu"):
        self.ocr = CnOcr()
        self.llm = llm or get_client()
        self.platform = platform
        self._use_last_h3 = False  # 最后一题时取视口底部 h3

        # 加载平台配置
        from config.platformConfig import get_platform_config
        self.cfg = get_platform_config(platform)

    def _get_text(self, item) -> str:
        if isinstance(item, dict) and "text" in item:
            return str(item["text"]).strip()
        elif isinstance(item, list) and len(item) > 0:
            return str(item[0]).strip()
        return ""

    def ocr_items(self, img_or_path) -> List[Any]:
        try:
            if isinstance(img_or_path, str):
                out = self.ocr.ocr(img_or_path)
            elif isinstance(img_or_path, Image.Image):
                out = self.ocr.ocr(np.array(img_or_path))
            else:
                out = self.ocr.ocr(img_or_path)
            return out or []
        except Exception as e:
            logger.error(f"OCR失败: {e}")
            return []

    def ocr_text(self, img_or_path) -> str:
        items = self.ocr_items(img_or_path)
        lines: List[str] = []
        for it in items:
            txt = self._get_text(it)
            if txt:
                lines.append(txt)
        text = "\n".join(lines)
        logger.debug(f"OCR提取{len(lines)}行")
        return text

    def screenshot_web_element(self, element: Any, save_crop_path: Optional[str] = None) -> Image.Image:
        try:
            if hasattr(element, "screenshot_as_png"):
                png_bytes = element.screenshot_as_png
                if save_crop_path:
                    try:
                        with open(save_crop_path, "wb") as f:
                            f.write(png_bytes)
                    except Exception as e:
                        logger.warning(f"调试保存元素截图失败: {e}")
                return Image.open(BytesIO(png_bytes)).convert("RGB")
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                ok = element.screenshot(tmp_path)
                if not ok:
                    raise RuntimeError("element.screenshot 返回失败")
                if save_crop_path:
                    try:
                        with open(save_crop_path, "wb") as f:
                            with open(tmp_path, "rb") as tmp_f:
                                f.write(tmp_f.read())
                    except Exception as e:
                        logger.warning(f"调试保存元素截图失败: {e}")
                return Image.open(tmp_path).convert("RGB")
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"元素截图失败: {e}")
            return Image.new("RGB", (0, 0))

    def _clean_qa_text(self, raw: str) -> str:
        import re as _re
        if not raw:
            return ""
        lines = raw.split('\n')
        clean = []
        skip_patterns = [
            r'暂存', r'提交作业', r'作业名称',
            r'对应章节', r'成绩类型', r'剩余时间', r'截止时间',
            r'题目数', r'总分数', r'说明', r'完成率', r'提示',
            r'^\d+天', r'^\d+时分', r'第\d+部分', r'总题数',
            r'上一题', r'下一题', r'Copyright', r'沪ICP', r'电子营业执照',
            r'在线学堂', r'^\d+$', r'^\d+%$', r'答题后请点', r'名称\s',
            r'试卷已提交', r'不能继续答题', r'已提交', r'保存',
            r'^\s*$', r'^[A-Z]\s*$', r'^\d+\s*$',
            r'答题后请点【下一题】', r'全部试题答完后',
            r'避免答题记录丢失', r'^\d+/\d+$',
        ]
        if self.platform == "zhihuishu":
            skip_patterns.extend([r'智慧树', r'Teenity'])
        elif self.platform == "chaoxing":
            skip_patterns.extend([r'超星', r'尔雅', r'学习通', r'章测试', r'测验', r'作业', r'单元'])
        for line in lines:
            s = line.strip()
            if not s or len(s) > 500:
                continue
            ignored = False
            for p in skip_patterns:
                if _re.search(p, s):
                    ignored = True
                    break
            if not ignored:
                clean.append(s)
        return '\n'.join(clean)

    def _has_real_question(self, text: str) -> bool:
        if not text or len(text.strip()) < 15:
            return False
        meta_keywords = ['第', '部分', '总题数', '上一题', '下一题', '答题后', '保存答案']
        lines = text.split('\n')
        meta_count = sum(1 for l in lines if any(kw in l for kw in meta_keywords))
        if meta_count >= len(lines) * 0.3:
            return False
        import re as _re
        real_lines = [l for l in lines if len(l) > 8 and not any(kw in l for kw in meta_keywords)]
        return len(real_lines) >= 1

    # ===== 考试页面：解答当前题目 =====
    def solve_exam_question(self, driver: Any, platform_cfg: Optional[Dict[str, Any]] = None) -> bool:
        if platform_cfg is not None and hasattr(platform_cfg, 'to_dict'):
            cfg = platform_cfg.to_dict()
        elif isinstance(platform_cfg, dict):
            cfg = platform_cfg
        elif hasattr(self, 'cfg') and self.cfg is not None:
            cfg = self.cfg.to_dict()
        else:
            cfg = {}

        card_selectors = cfg.get("card_selectors", [])
        option_selectors = cfg.get("option_selectors", [])

        # ---- 通过当前选中题号定位题目 ----
        card_info = driver.execute_script(r"""
            // 清除旧标记
            var old = document.querySelectorAll('[__opt_idx__]');
            for (var oi = 0; oi < old.length; oi++) {
                old[oi].removeAttribute('__opt_idx__');
                old[oi].removeAttribute('__opt_text__');
            }

            // 找当前题 h3
            var h3s = document.querySelectorAll('h3.mark_name, h3[class*="mark_name"]');
            var vh = window.innerHeight;
            var currentH3 = null;
            var useLast = """ + json.dumps(self._use_last_h3) + r""";
            if (useLast) {
                // 最后一题页面滚不动，取视口内最后一个 h3
                for (var i = h3s.length - 1; i >= 0; i--) {
                    var r = h3s[i].getBoundingClientRect();
                    if (r.top >= -10 && r.top < vh && h3s[i].offsetParent !== null) {
                        currentH3 = h3s[i]; break;
                    }
                }
            } else {
                // 正常取第一个
                for (var i = 0; i < h3s.length; i++) {
                    var r = h3s[i].getBoundingClientRect();
                    if (r.top >= -10 && r.top < vh && h3s[i].offsetParent !== null) {
                        currentH3 = h3s[i]; break;
                    }
                }
            }
            // 兜底：取第一个有内容的 h3
            if (!currentH3) {
                for (var j = 0; j < h3s.length; j++) {
                    if (h3s[j].offsetParent !== null && (h3s[j].innerText || '').trim().length > 3) {
                        currentH3 = h3s[j]; break;
                    }
                }
            }

            // 3. 找紧随 stem_answer
            var stem = null;
            if (currentH3) {
                var next = currentH3.nextElementSibling;
                while (next) {
                    if (next.classList && next.classList.contains('stem_answer')) {
                        stem = next; break;
                    }
                    var inner = next.querySelector('div.stem_answer');
                    if (inner) { stem = inner; break; }
                    next = next.nextElementSibling;
                }
            }

            // 4. 在 stem 内找选项
            var optionEls = [];
            if (stem) {
                var roles = stem.querySelectorAll("div[role='radio'], div[role='checkbox']");
                for (var r3 = 0; r3 < roles.length; r3++) {
                    optionEls.push(roles[r3]);
                }
            }
            // 回退：全局找
            if (optionEls.length < 2 && stem) {
                var all = stem.querySelectorAll('div, li, span, label, p');
                for (var a = 0; a < all.length; a++) {
                    var t = (all[a].innerText || all[a].textContent || '').trim();
                    if (/^[A-Z]\s/.test(t) && t.length > 1 && t.length < 300) {
                        if (optionEls.indexOf(all[a]) < 0) optionEls.push(all[a]);
                    }
                }
            }

            // 5. 去重
            var deduped = [];
            for (var d = 0; d < optionEls.length; d++) {
                var isChild = false;
                for (var e = 0; e < optionEls.length; e++) {
                    if (d !== e && optionEls[e].contains(optionEls[d]) && optionEls[e] !== optionEls[d]) {
                        isChild = true; break;
                    }
                }
                if (!isChild) deduped.push(optionEls[d]);
            }

            // 6. 标记：提取选项文本（字母 + 内容，去多余换行）
            for (var y = 0; y < deduped.length; y++) {
                var el = deduped[y];
                var raw = (el.innerText || el.textContent || '').trim();
                // 压缩空白：多个空格/换行变成一个空格
                var txt = raw.replace(/\s+/g, ' ').trim();
                deduped[y].setAttribute('__opt_idx__', y);
                deduped[y].setAttribute('__opt_text__', txt);
            }

            // 7. 题目文本：h3 + 选项（一行一个）
            var domText = '';
            if (currentH3) {
                domText = (currentH3.innerText || currentH3.textContent || '').trim().replace(/\s+/g, ' ');
            }
            for (var y2 = 0; y2 < deduped.length; y2++) {
                domText += '\n' + (deduped[y2].getAttribute('__opt_text__') || '');
            }
            if (!domText || domText.length < 15) {
                domText = (stem ? (stem.innerText || stem.textContent || '') : (document.body.innerText || document.body.textContent || '')).trim();
            }

            return {
                optionCount: deduped.length,
                domText: domText
            };
        """)

        opt_count = (card_info or {}).get("optionCount", 0) if card_info else 0
        logger.debug(f"找到 {opt_count} 个选项元素")

        # ---- DOM 文本 ----
        dom_text = (card_info or {}).get("domText", "") if card_info else ""
        dom_text = (dom_text or "").strip()
        dom_clean = self._clean_qa_text(dom_text) if dom_text else ""
        logger.debug(f"DOM 原始文本({len(dom_text)}字): {dom_text[:200]}")
        logger.debug(f"DOM 清洗后({len(dom_clean)}字): {dom_clean[:200]}")

        # 学习通 DOM 文本已足够精准，跳过 OCR；智慧树才需要 OCR 做双路径
        if self.platform == "chaoxing":
            qa_text = dom_clean
            if not qa_text or len(qa_text) < 15:
                qa_text = self._screenshot_question_card(driver)
                qa_text = self._clean_qa_text(qa_text) if qa_text else ""
                logger.info("DOM 文本不足，回退到 OCR。")
            else:
                logger.info("使用 DOM 文本。")
        else:
            # ---- OCR 双路径（智慧树）----
            ocr_text = self._screenshot_question_card(driver)
            ocr_clean = self._clean_qa_text(ocr_text) if ocr_text else ""
            logger.debug(f"OCR 原始文本({len(ocr_text)}字): {ocr_text[:200]}")
            logger.debug(f"OCR 清洗后({len(ocr_clean)}字): {ocr_clean[:200]}")

            dom_has_real = self._has_real_question(dom_clean)
            ocr_has_real = self._has_real_question(ocr_clean)

            if ocr_has_real and dom_has_real:
                qa_text = ocr_clean if len(ocr_clean) > len(dom_clean) * 1.3 else dom_clean
                logger.info("DOM+OCR 均有内容，择优使用。")
            elif ocr_has_real:
                qa_text = ocr_clean
            elif dom_has_real:
                qa_text = dom_clean
            elif dom_clean and len(dom_clean) >= 15:
                qa_text = dom_clean
            elif ocr_clean and len(ocr_clean) >= 15:
                qa_text = ocr_clean
            else:
                qa_text = dom_clean or ocr_clean or ""
        if len(qa_text) < 5:
                qa_text = self._dom_text_fallback(driver)
                qa_text = self._clean_qa_text(qa_text)

        if not qa_text or len(qa_text.strip()) < 5:
            logger.error("无法获取题目文本。")
            return False

        logger.info(f"题目文本({len(qa_text)}字): {qa_text[:300]}")

        # 保存调试文件
        try:
            from pathlib import Path
            debug_dir = Path("debug")
            debug_dir.mkdir(exist_ok=True)
            import datetime
            ts = datetime.datetime.now().strftime("%H%M%S")
            (debug_dir / f"qa_{ts}.txt").write_text(qa_text, encoding="utf-8")
        except Exception:
            pass

        # ---- LLM ----
        selected: List[str] = []
        try:
            result = self.llm.answer_question(qa_text)
            if isinstance(result, dict):
                sel = result.get("selected")
                if isinstance(sel, list):
                    selected = [str(s).strip() for s in sel]
        except Exception as e:
            logger.error(f"LLM 异常: {e}")
            return False

        if not selected:
            selected = ["A"]
        logger.info(f"LLM 答案: {selected}")

        # ---- 点击选项 ----
        return self._click_exam_options(driver, selected)

    def _screenshot_question_card(self, driver: Any) -> str:
        """截取当前视口内第一道题的 (h3 + stem_answer) 区域。"""
        try:
            from PIL import Image
            from io import BytesIO

            # 全页截图
            png = driver.get_screenshot_as_png()
            full = Image.open(BytesIO(png)).convert("RGB")

            # 找当前题目对应的 h3 和 stem_answer
            # 策略：视口内第一个可见的 h3.mark_name 就是当前题
            # 然后找紧随其后的 div.stem_answer
            crop_rect = driver.execute_script(r"""
                var vh = window.innerHeight;
                function inView(el) {
                    if (!el || el.offsetParent === null) return false;
                    var r = el.getBoundingClientRect();
                    return r.top >= -10 && r.top < vh * 0.7;
                }

                // 找视口内第一个可见的 h3
                var h3s = document.querySelectorAll('h3.mark_name, h3[class*="mark_name"]');
                var currentH3 = null;
                for (var i = 0; i < h3s.length; i++) {
                    if (inView(h3s[i])) {
                        currentH3 = h3s[i];
                        break;
                    }
                }
                if (!currentH3) return null;

                // 找这个 h3 后面的 div.stem_answer（h3 + clear + div.stem_answer 结构）
                var stem = null;
                var next = currentH3.nextElementSibling;
                while (next && (!stem || stem === null)) {
                    if (next.tagName === 'DIV' && next.className && next.className.indexOf('stem_answer') >= 0) {
                        stem = next;
                        break;
                    }
                    // 也检查后代
                    var inner = next.querySelector('div.stem_answer');
                    if (inner) {
                        stem = inner;
                        break;
                    }
                    next = next.nextElementSibling;
                }
                if (!stem) return null;

                var sx = window.scrollX || window.pageXOffset;
                var sy = window.scrollY || window.pageYOffset;
                var h3Rect = currentH3.getBoundingClientRect();
                var stemRect = stem.getBoundingClientRect();

                return {
                    left:   Math.min(h3Rect.left, stemRect.left) + sx,
                    top:    h3Rect.top + sy,
                    right:  Math.max(h3Rect.right, stemRect.right) + sx,
                    bottom: stemRect.bottom + sy
                };
            """)

            if crop_rect:
                l = max(0, int(crop_rect["left"]))
                t = max(0, int(crop_rect["top"]))
                r = max(l + 10, min(int(crop_rect["right"]), full.width))
                b = max(t + 10, min(int(crop_rect["bottom"]), full.height))
                crop = full.crop((l, t, r, b))
            else:
                # 回退：截取视口
                si = driver.execute_script(r"""return {
                    sx: window.scrollX || window.pageXOffset,
                    sy: window.scrollY || window.pageYOffset,
                    w: window.innerWidth,
                    h: window.innerHeight
                };""")
                sx, sy, vw, vh = int(si["sx"]), int(si["sy"]), int(si["w"]), int(si["h"])
                crop = full.crop((sx, sy, min(sx + vw, full.width), min(sy + vh, full.height)))

            # 调试保存
            try:
                from pathlib import Path
                import datetime
                debug_dir = Path("debug")
                debug_dir.mkdir(exist_ok=True)
                ts = datetime.datetime.now().strftime("%H%M%S")
                crop.save(str(debug_dir / f"ocr_{ts}.png"))
                logger.debug(f"OCR 截图已保存到 debug/ocr_{ts}.png")
            except Exception:
                pass

            raw = self.ocr_text(crop)
            if raw and len(raw.strip()) > 10:
                logger.debug(f"OCR 题目截图成功，{len(raw)} 字")
            return raw
        except Exception as e:
            logger.error(f"截图 OCR 失败: {e}")
            return ""

    def _dom_text_fallback(self, driver: Any) -> str:
        import re as _re
        try:
            container_text = driver.execute_script("""
                var selectors = [
                    '[class*="topic"]', '[class*="subject"]', '[class*="question"]',
                    '[class*="stem"]', '[class*="exam"]', '[class*="ques"]',
                    '.el-card__body', '.el-card', '.el-dialog__body',
                    'article', 'main', '[role="main"]', 'h3.mark_name'
                ];
                var best = '';
                for (var s = 0; s < selectors.length; s++) {
                    try {
                        var els = document.querySelectorAll(selectors[s]);
                        for (var e = 0; e < els.length; e++) {
                            if (els[e].offsetParent === null) continue;
                            var txt = (els[e].innerText || els[e].textContent || '').trim();
                            if (txt.length > best.length && txt.length >= 20 && txt.length < 8000) {
                                var hasOpt = /[A-Z][.、)）]/.test(txt);
                                if (hasOpt || best === '' || txt.length > best.length * 1.5) {
                                    best = txt;
                                }
                            }
                        }
                    } catch(e) {}
                }
                return best;
            """) or ""
            if container_text and len(container_text.strip()) >= 10:
                return container_text
            raw = driver.execute_script("return document.body.innerText || document.body.textContent || '';") or ""
            return raw
        except Exception:
            return ""

    # ===== 点击选项（学习通用 addChoice 函数）=====
    def _click_exam_options(self, driver: Any, selected: List[str]) -> bool:
        """
        对于 learning 通：调用页面全局 addChoice(el) 函数
        它内部会设置 aria-checked="true" 和发请求
        """
        opt_data = driver.execute_script("""
            var els = document.querySelectorAll('[__opt_idx__]');
            var result = [];
            for (var i = 0; i < els.length; i++) {
                result.push({
                    idx: parseInt(els[i].getAttribute('__opt_idx__')),
                    text: els[i].getAttribute('__opt_text__') || ''
                });
            }
            return result;
        """)

        if not opt_data:
            logger.warning("未找到标记选项，使用通用点击。")
            return self._click_options_fallback(driver, selected)

        logger.info(f"共 {len(opt_data)} 个选项，目标: {selected}")
        for o in opt_data:
            logger.debug(f"  选项[{o['idx']}]: {o['text'][:80]}")

        clicked = set()
        is_multi = len(selected) > 1  # 多选题需要更大延迟和重新查DOM

        for ans in selected:
            ans_upper = str(ans).strip().upper()
            if not ans_upper:
                continue
            matched = False
            # 多选题每个选项之间延迟加大（0.8~1.3s），给 addChoice 时间发请求
            delay = (0.8 + __import__('random').random() * 0.5) if is_multi else (0.3 + __import__('random').random() * 0.5)
            sleep(delay)

            # 多选题：每次点击前重新查当前第几个索引对应哪个DOM元素
            # 因为 addChoice 可能触发DOM变动，旧的 __opt_idx__ 标记会失效
            if is_multi:
                opt_data = driver.execute_script("""
                    var els = document.querySelectorAll('[__opt_idx__]');
                    var result = [];
                    for (var i = 0; i < els.length; i++) {
                        result.push({
                            idx: parseInt(els[i].getAttribute('__opt_idx__')),
                            text: els[i].getAttribute('__opt_text__') || ''
                        });
                    }
                    return result;
                """)
                if not opt_data:
                    continue

            # 字母索引
            if len(ans_upper) == 1 and ans_upper[0].isalpha():
                idx = ord(ans_upper[0]) - ord('A')
                if 0 <= idx < len(opt_data) and idx not in clicked:
                    if self._js_add_choice(driver, idx):
                        clicked.add(idx)
                        logger.info(f"字母点击 {ans_upper} -> 选项[{idx}]: {opt_data[idx]['text'][:50]}")
                        matched = True

            # 文本匹配
            if not matched:
                for item in opt_data:
                    i = item["idx"]
                    if i in clicked:
                        continue
                    txt_u = (item["text"] or "").upper()
                    if ans_upper in txt_u or txt_u.startswith(ans_upper):
                        if self._js_add_choice(driver, i):
                            clicked.add(i)
                            logger.info(f"文本点击 -> 选项[{i}]: {item['text'][:50]}")
                            matched = True
                            break

            # 判断题
            if not matched:
                tf_keywords = {
                    "对": ["对", "正确"], "错": ["错", "错误"],
                }
                for kw in tf_keywords.get(ans_upper, []):
                    for item in opt_data:
                        i = item["idx"]
                        if i in clicked:
                            continue
                        if kw in (item["text"] or ""):
                            if self._js_add_choice(driver, i):
                                clicked.add(i)
                                logger.info(f"判断点击 -> 选项[{i}]")
                                matched = True
                                break
                    if matched:
                        break

            if not matched:
                logger.warning(f"未能匹配答案 '{ans_upper}' 到选项")

        # 保底
        if not clicked and opt_data:
            logger.warning("默认点击 A")
            self._js_add_choice(driver, 0)
            clicked.add(0)

        # 验证（只看当前 stem_answer 内）
        sleep(0.6)
        verified = driver.execute_script(r"""
            var vh = window.innerHeight;
            var stem = null;
            var h3s = document.querySelectorAll('h3.mark_name');
            for (var hi = 0; hi < h3s.length; hi++) {
                var r = h3s[hi].getBoundingClientRect();
                if (r.top >= -10 && r.top < vh * 0.7 && h3s[hi].offsetParent !== null) {
                    var next = h3s[hi].nextElementSibling;
                    while (next) {
                        if (next.classList && next.classList.contains('stem_answer')) { stem = next; break; }
                        next = next.nextElementSibling;
                    }
                    break;
                }
            }
            if (!stem) return {ariaChecked: -1, inputChecked: -1};
            var checked = stem.querySelectorAll('[aria-checked="true"]');
            var inputs = stem.querySelectorAll('input[type="radio"]:checked, input[type="checkbox"]:checked');
            return {ariaChecked: checked.length, inputChecked: inputs.length};
        """)
        logger.info(f"选中验证: aria-checked={verified.get('ariaChecked',0)}, input选中={verified.get('inputChecked',0)}")
        return True

    def _js_add_choice(self, driver: Any, idx: int) -> bool:
        """用 Selenium 浏览器级点击触发 onclick='addChoice(this)'"""
        from selenium.webdriver.common.by import By

        # 先尝试通过标记找到元素
        el = None
        try:
            el = driver.find_element(By.CSS_SELECTOR, f'[__opt_idx__="{idx}"]')
        except Exception:
            pass

        # 标记丢失：从当前题 stem_answer 按索引取
        if not el:
            stems = driver.find_elements(By.CSS_SELECTOR, "div.stem_answer")
            for s in stems:
                if s.is_displayed():
                    opts = s.find_elements(By.CSS_SELECTOR, "div[role='radio'], div[role='checkbox']")
                    if idx < len(opts):
                        el = opts[idx]
                        break

        if not el:
            return False
        try:
            el.click()
            return True
        except Exception:
            return False

    def _click_options_fallback(self, driver: Any, selected: List[str]) -> bool:
        """查找所有可点击选项并点击"""
        options = driver.execute_script("""
            var all = [];
            var roles = document.querySelectorAll("div[role='radio'], div[role='checkbox'], div[class*='answerBg']");
            for (var i = 0; i < roles.length; i++) {
                if (roles[i].offsetParent !== null) all.push(roles[i]);
            }
            if (all.length === 0) {
                var inputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                for (var j = 0; j < inputs.length; j++) all.push(inputs[j]);
            }
            return all;
        """)

        if not options:
            logger.error("找不到选项。")
            return False

        logger.info(f"回退找到 {len(options)} 个选项")

        def fallback_mouse_click(target_el):
            try:
                target_el.click()
            except Exception:
                pass

        clicked = set()
        for ans in selected:
            ans_upper = str(ans).strip().upper()
            if ans_upper and len(ans_upper) == 1 and ans_upper[0].isalpha():
                idx = ord(ans_upper[0]) - ord('A')
                if 0 <= idx < len(options) and idx not in clicked:
                    fallback_mouse_click(options[idx])
                    clicked.add(idx)
                    logger.info(f"回退点击 {ans_upper}")
                    sleep(0.3 + __import__('random').random() * 0.5)
                    continue
            for i, el in enumerate(options):
                if i in clicked:
                    continue
                try:
                    txt = driver.execute_script("return arguments[0].innerText || arguments[0].textContent || '';", el) or ""
                except Exception:
                    txt = ""
                if ans_upper in txt.upper():
                    fallback_mouse_click(el)
                    clicked.add(i)
                    sleep(0.3 + __import__('random').random() * 0.5)
                    break

        if not clicked and options:
            fallback_mouse_click(options[0])
        return True

    # ===== 已废弃的方法（智慧树原版）保留以备兼容 =====
    def solve_answers_from_image(self, element: Any = None, save_crop_path: Optional[str] = None, driver: Any = None) -> bool:
        """旧方法，不再使用，保留兼容"""
        return False
