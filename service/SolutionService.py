import numpy as np
import tempfile
import os

from typing import List, Any, Optional
from PIL import Image
from loguru import logger
from cnocr import CnOcr
from tools.llms.DeepSeek import DeepSeek, get_client
from io import BytesIO
from time import sleep


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

class SolutionService:
    def __init__(self, llm: Optional[DeepSeek] = None):
        self.ocr = CnOcr()
        self.llm = llm or get_client()

    def _get_text(self, item) -> str:
        if isinstance(item, dict) and "text" in item:
            return str(item["text"]).strip()
        elif isinstance(item, list) and len(item) > 0:
            return str(item[0]).strip()
        return ""

    def ocr_items(self, img_or_path) -> List[Any]:
        """
        执行 OCR，接受图片路径、PIL.Image 或 numpy 数组。
        返回原始识别项列表（字典/列表混合）。
        """
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
        """执行 OCR 并返回拼接后的文本。"""
        items = self.ocr_items(img_or_path)
        lines: List[str] = []
        for it in items:
            txt = self._get_text(it)
            if txt:
                lines.append(txt)
        text = "\n".join(lines)
        logger.debug(f"OCR提取{len(lines)}行")
        return text

    # 对指定元素图片进行 截屏
    def screenshot_web_element(self, element: Any, save_crop_path: Optional[str] = None) -> Image.Image:
        try:
            # 优先使用 screenshot_as_png 直接获取内存字节
            if hasattr(element, "screenshot_as_png"):
                png_bytes = element.screenshot_as_png
                if save_crop_path:
                    try:
                        with open(save_crop_path, "wb") as f:
                            f.write(png_bytes)
                    except Exception as e:
                        logger.warning(f"调试保存元素截图失败: {e}")
                return Image.open(BytesIO(png_bytes)).convert("RGB")
            # 兼容不支持属性的驱动，使用临时文件保存再读取
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                ok = element.screenshot(tmp_path)
                if not ok:
                    raise RuntimeError("element.screenshot 返回失败")
                # 若需要保存到指定路径，拷贝一份方便调试
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
        """清洗题目文本，去除页面元数据噪声。"""
        import re as _re
        if not raw:
            return ""
        lines = raw.split('\n')
        clean = []
        skip = [
            r'智慧树', r'Teenity', r'暂存', r'提交作业', r'作业名称',
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
        for line in lines:
            s = line.strip()
            if not s or len(s) > 500:
                continue
            ignored = False
            for p in skip:
                if _re.search(p, s):
                    ignored = True
                    break
            if not ignored:
                clean.append(s)
        return '\n'.join(clean)

    def _has_real_question(self, text: str) -> bool:
        """检测文本是否包含真正的题目内容（而非仅有页面元数据）。"""
        if not text or len(text.strip()) < 15:
            return False
        # 元数据关键词占比过高则判定为无真实题目
        meta_keywords = ['第', '部分', '总题数', '上一题', '下一题', '答题后', '保存答案']
        lines = text.split('\n')
        meta_count = sum(1 for l in lines if any(kw in l for kw in meta_keywords))
        if meta_count >= len(lines) * 0.3:
            return False
        # 必须包含一定长度的非元数据行
        import re as _re
        real_lines = [l for l in lines if len(l) > 8 and not any(kw in l for kw in meta_keywords)]
        return len(real_lines) >= 1

    # 考试页面：解答当前题目
    def solve_exam_question(self, driver: Any) -> bool:
        """DOM 文本 + OCR 双路径提取，确保图片题目也能识别。"""

        # 1. 找题目卡片区域、选项元素，同时提取 DOM 文本
        card_info = driver.execute_script("""
            // 清除旧标记
            var old = document.querySelectorAll('[__opt_idx__]');
            for (var oi = 0; oi < old.length; oi++) {
                old[oi].removeAttribute('__opt_idx__');
                old[oi].removeAttribute('__opt_text__');
            }

            // 找题目卡片: 包含选项的最小可见区域
            var cardSelectors = [
                '.question-card', '.exam-card', '.topic-card',
                '[class*="question"]', '[class*="topic-detail"]',
                '.el-card', '.paper-item', '.exam-item',
                // 智慧树新版
                '.topic-item', '.topic-box', '.subject-box',
                '.ques-card-box', '.ques-item', '[class*="ques"]',
                '[class*="stem-box"]', '[class*="subject"]',
                // 通用
                '.el-dialog__body', '[class*="exam-area"]'
            ];
            var card = null;
            for (var cs = 0; cs < cardSelectors.length; cs++) {
                try {
                    var c = document.querySelector(cardSelectors[cs]);
                    if (c && c.offsetParent !== null) {
                        card = c;
                        break;
                    }
                } catch(e) {}
            }
            // 回退: 找同时包含选项的最小公共祖先
            if (!card) {
                var maybeOpts = document.querySelectorAll(
                    'li[class*="option"], div[class*="option"], .options li'
                );
                if (maybeOpts.length >= 2) {
                    card = maybeOpts[0].parentElement;
                    while (card && card !== document.body &&
                           card.querySelectorAll('li[class*="option"], div[class*="option"]').length === maybeOpts.length) {
                        card = card.parentElement;
                    }
                }
            }

            // 找选项元素
            var optionEls = [];
            // 策略1: 选项结构类（Element UI / 智慧树 / 通用）
            var opts = document.querySelectorAll(
                '.option, .option-item, .choice-item, li[class*="option"], ' +
                'div[class*="option-item"], .options>li, .options>div, ' +
                '.answer-option, [class*="exam-option"], ' +
                '.el-radio, label.el-radio, .radio-item, ' +
                '.check-item, .radio-wrap, [class*="option-wrap"], ' +
                '[class*="topic-option"], [class*="option-box"], ' +
                '.answer-item, [class*="answer-item"]'
            );
            for (var o = 0; o < opts.length; o++) {
                if (opts[o].offsetParent !== null) {
                    // input 元素没有 innerText，但包含 input 的容器可以接受
                    var hasInput = opts[o].querySelector('input[type="radio"], input[type="checkbox"]');
                    var txtLen = (opts[o].innerText || opts[o].textContent || '').trim().length;
                    if (txtLen > 1 || hasInput) {
                        optionEls.push(opts[o]);
                    }
                }
            }
            // 策略2: radio/checkbox 的 label — 始终执行
            var radios = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
            var visRadios = [];
            for (var r = 0; r < radios.length; r++) {
                if (radios[r].offsetParent !== null) visRadios.push(radios[r]);
            }
            if (optionEls.length < visRadios.length) {
                for (var r2 = 0; r2 < visRadios.length; r2++) {
                    var lbl = visRadios[r2].closest('label') ||
                               (visRadios[r2].id ? document.querySelector('label[for="' + visRadios[r2].id + '"]') : null) ||
                               visRadios[r2].parentElement;
                    if (lbl && lbl.offsetParent !== null && optionEls.indexOf(lbl) < 0) {
                        optionEls.push(lbl);
                    }
                }
            }
            // 策略3: 文本以 A/B/C/D 开头且只含单个选项
            if (optionEls.length < 2) {
                var all = document.querySelectorAll('div, li, span, label, p');
                for (var a = 0; a < all.length; a++) {
                    var t = (all[a].innerText || all[a].textContent || '').trim();
                    if (t.length > 1 && t.length < 300 && /^[A-Z][.、)\\s]/.test(t)) {
                        var rest = t.substring(2);
                        if (!/[B-Z][.、)\\s]/.test(rest)) {
                            if (all[a].offsetParent !== null) optionEls.push(all[a]);
                        }
                    }
                }
            }
            // 去重（排除父子嵌套）
            var deduped = [];
            for (var d = 0; d < optionEls.length; d++) {
                var isChild = false;
                for (var e = 0; e < optionEls.length; e++) {
                    if (d !== e && optionEls[e].contains(optionEls[d]) &&
                        optionEls[e] !== optionEls[d]) {
                        isChild = true; break;
                    }
                }
                if (!isChild) deduped.push(optionEls[d]);
            }
            // 标记
            for (var y = 0; y < deduped.length; y++) {
                var el = deduped[y];
                var txt = (el.innerText || el.textContent || '').trim();
                // input 元素没有 innerText，从 label 或父元素获取
                if (!txt && el.tagName === 'INPUT') {
                    var lblForInput = el.closest('label');
                    if (lblForInput) txt = (lblForInput.innerText || lblForInput.textContent || '').trim();
                    if (!txt) {
                        var par = el.parentElement;
                        if (par) txt = (par.innerText || par.textContent || '').trim();
                    }
                }
                // 如果文本短或是空的，尝试从父元素获取
                if (txt.length <= 3) {
                    var p = el.parentElement;
                    if (p) {
                        var pTxt = (p.innerText || p.textContent || '').trim();
                        if (pTxt.length > txt.length) txt = pTxt;
                    }
                }
                // 合并下一个兄弟元素文本
                if (txt.length <= 3) {
                    var ns = el.nextElementSibling;
                    if (ns) {
                        var nsTxt = (ns.innerText || ns.textContent || '').trim();
                        if (nsTxt && !/^[A-Z][.)\\s]*$/.test(nsTxt)) {
                            txt = txt ? txt + ' ' + nsTxt : nsTxt;
                        }
                    }
                }
                // 如果还是空，尝试从包含的 label 获取
                if (!txt) {
                    var innerLabel = el.querySelector('label');
                    if (innerLabel) txt = (innerLabel.innerText || innerLabel.textContent || '').trim();
                }
                deduped[y].setAttribute('__opt_idx__', y);
                deduped[y].setAttribute('__opt_text__', txt);
            }
            // 提取 DOM 文本（从卡片或 best 容器）
            var domText = '';
            function extractText(el) {
                if (!el) return '';
                // 克隆节点避免修改原始 DOM
                var clone = el.cloneNode(true);
                // 移除 script/style 标签
                var removes = clone.querySelectorAll('script, style, noscript, [aria-hidden="true"]');
                for (var rm = 0; rm < removes.length; rm++) {
                    removes[rm].parentNode.removeChild(removes[rm]);
                }
                return (clone.innerText || clone.textContent || '').trim();
            }
            if (card) {
                domText = extractText(card);
            }
            if (!domText || domText.length < 20) {
                // 回退：找最可能的题目容器
                var containers = document.querySelectorAll(
                    '[class*="topic"], [class*="subject"], [class*="question"], ' +
                    '[class*="stem"], [class*="exam"], .el-card__body'
                );
                var bestTxt = '';
                for (var ct = 0; ct < containers.length; ct++) {
                    if (containers[ct].offsetParent === null) continue;
                    var t = (containers[ct].innerText || containers[ct].textContent || '').trim();
                    if (t.length > bestTxt.length && t.length < 5000) {
                        bestTxt = t;
                    }
                }
                if (bestTxt) domText = bestTxt;
            }
            return {
                cardFound: !!card,
                optionCount: deduped.length,
                domText: domText
            };
        """)

        opt_count = (card_info or {}).get("optionCount", 0) if card_info else 0
        logger.debug(f"找到 {opt_count} 个选项元素")

        # 2. 双路径提取：DOM 文本 + OCR 截图，取最佳结果
        dom_text = (card_info or {}).get("domText", "") if card_info else ""
        dom_text = (dom_text or "").strip()
        dom_clean = self._clean_qa_text(dom_text) if dom_text else ""
        logger.debug(f"DOM 原始文本({len(dom_text)}字): {dom_text[:200]}")
        logger.debug(f"DOM 清洗后({len(dom_clean)}字): {dom_clean[:200]}")

        # 始终尝试 OCR（捕获图片中的题目文字），取非空结果
        ocr_text = self._screenshot_question_card(driver)
        ocr_clean = self._clean_qa_text(ocr_text) if ocr_text else ""
        logger.debug(f"OCR 原始文本({len(ocr_text)}字): {ocr_text[:200]}")
        logger.debug(f"OCR 清洗后({len(ocr_clean)}字): {ocr_clean[:200]}")

        # 合并策略：OCR 通常更完整（含图片文字），DOM 选项文本更精准
        qa_text = ""
        dom_has_real = self._has_real_question(dom_clean)
        ocr_has_real = self._has_real_question(ocr_clean)

        if ocr_has_real and dom_has_real:
            # 两者都有内容：DOM 优先（文字精准），但 OCR 补充图片文字
            # 如果 OCR 更长（含图片文字），用 OCR；否则用 DOM
            qa_text = ocr_clean if len(ocr_clean) > len(dom_clean) * 1.3 else dom_clean
            logger.info("DOM+OCR 均有内容，择优使用。")
        elif ocr_has_real:
            qa_text = ocr_clean
            logger.info("OCR 含真实题目内容，使用 OCR 结果。")
        elif dom_has_real:
            qa_text = dom_clean
            logger.info("DOM 含真实题目内容，使用 DOM 结果。")
        elif dom_clean and len(dom_clean) >= 15:
            qa_text = dom_clean
            logger.warning("DOM/OCR 均无明确题目内容，回退使用 DOM 文本。")
        elif ocr_clean and len(ocr_clean) >= 15:
            qa_text = ocr_clean
            logger.warning("DOM/OCR 均无明确题目内容，回退使用 OCR 文本。")
        else:
            # 最终回退
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
            logger.debug(f"题目文本已保存到 debug/qa_{ts}.txt")
        except Exception:
            pass

        # 3. LLM
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

        # 重新标记选项元素（Vue.js 可能在 LLM 调用期间重新渲染 DOM）
        remark_count = driver.execute_script("""
            var old = document.querySelectorAll('[__opt_idx__]');
            for (var oi = 0; oi < old.length; oi++) {
                old[oi].removeAttribute('__opt_idx__');
                old[oi].removeAttribute('__opt_text__');
            }
            var optionEls = [];
            var opts = document.querySelectorAll(
                '.option, .option-item, .choice-item, li[class*="option"], ' +
                'div[class*="option-item"], .options>li, .options>div, ' +
                '.answer-option, [class*="exam-option"], ' +
                '.el-radio, label.el-radio, .radio-item, ' +
                '.check-item, .radio-wrap, [class*="option-wrap"], ' +
                '[class*="topic-option"], [class*="option-box"], ' +
                '.answer-item, [class*="answer-item"]'
            );
            for (var o = 0; o < opts.length; o++) {
                if (opts[o].offsetParent !== null) {
                    var hasInput2 = opts[o].querySelector('input[type="radio"], input[type="checkbox"]');
                    var txtLen2 = (opts[o].innerText || opts[o].textContent || '').trim().length;
                    if (txtLen2 > 1 || hasInput2) {
                        optionEls.push(opts[o]);
                    }
                }
            }
            var radios2 = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
            var visRadios2 = [];
            for (var r = 0; r < radios2.length; r++) {
                if (radios2[r].offsetParent !== null) visRadios2.push(radios2[r]);
            }
            if (optionEls.length < visRadios2.length) {
                for (var r2 = 0; r2 < visRadios2.length; r2++) {
                    var lbl = visRadios2[r2].closest('label') ||
                               (visRadios2[r2].id ? document.querySelector('label[for="' + visRadios2[r2].id + '"]') : null) ||
                               visRadios2[r2].parentElement;
                    if (lbl && lbl.offsetParent !== null && optionEls.indexOf(lbl) < 0) {
                        optionEls.push(lbl);
                    }
                }
            }
            if (optionEls.length < 2) {
                var all2 = document.querySelectorAll('div, li, span, label, p');
                for (var a = 0; a < all2.length; a++) {
                    var t = (all2[a].innerText || all2[a].textContent || '').trim();
                    if (t.length > 1 && t.length < 300 && /^[A-Z][.、)\\s]/.test(t)) {
                        var rest = t.substring(2);
                        if (!/[B-Z][.、)\\s]/.test(rest)) {
                            if (all2[a].offsetParent !== null) optionEls.push(all2[a]);
                        }
                    }
                }
            }
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
            for (var y = 0; y < deduped.length; y++) {
                var el = deduped[y];
                var txt = (el.innerText || el.textContent || '').trim();
                // input 元素没有 innerText，从 label 或父元素获取
                if (!txt && el.tagName === 'INPUT') {
                    var lblForInput = el.closest('label');
                    if (lblForInput) txt = (lblForInput.innerText || lblForInput.textContent || '').trim();
                    if (!txt) {
                        var par2 = el.parentElement;
                        if (par2) txt = (par2.innerText || par2.textContent || '').trim();
                    }
                }
                if (txt.length <= 3) {
                    var p = el.parentElement;
                    if (p) {
                        var pTxt = (p.innerText || p.textContent || '').trim();
                        if (pTxt.length > txt.length) txt = pTxt;
                    }
                }
                if (txt.length <= 3) {
                    var ns = el.nextElementSibling;
                    if (ns) {
                        var nsTxt = (ns.innerText || ns.textContent || '').trim();
                        if (nsTxt && !/^[A-Z][.)\\s]*$/.test(nsTxt)) {
                            txt = txt ? txt + ' ' + nsTxt : nsTxt;
                        }
                    }
                }
                if (!txt) {
                    var innerLabel = el.querySelector('label');
                    if (innerLabel) txt = (innerLabel.innerText || innerLabel.textContent || '').trim();
                }
                deduped[y].setAttribute('__opt_idx__', y);
                deduped[y].setAttribute('__opt_text__', txt);
            }
            return deduped.length;
        """)
        logger.debug(f"重新标记了 {remark_count} 个选项元素")

        # 4. 点击选项
        return self._click_exam_options(driver, selected, qa_text)

    def _screenshot_question_card(self, driver: Any) -> str:
        """截图题目卡片区域做 OCR，优先捕获大范围区域以包含图片题目。"""
        import re as _re
        try:
            card = driver.execute_script("""
                // 策略1：找包含题目+选项的最大可见容器
                // 先找所有可见的 radio/checkbox
                var inputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                var visibleInputs = [];
                for (var i = 0; i < inputs.length; i++) {
                    if (inputs[i].offsetParent !== null) visibleInputs.push(inputs[i]);
                }
                if (visibleInputs.length >= 2) {
                    // 往上找最合适级别的祖先
                    var ancestor = visibleInputs[0].parentElement;
                    for (var up = 0; up < 10; up++) {
                        if (!ancestor || ancestor === document.body) break;
                        var containsAll = true;
                        for (var v = 0; v < visibleInputs.length; v++) {
                            if (!ancestor.contains(visibleInputs[v])) {
                                containsAll = false; break;
                            }
                        }
                        var txtLen = (ancestor.innerText || ancestor.textContent || '').length;
                        if (containsAll && txtLen > 50) {
                            return ancestor;
                        }
                        ancestor = ancestor.parentElement;
                    }
                }
                // 策略2：选项文本元素向上查找公共祖先
                var optLike = document.querySelectorAll('div, li, span, label, p, dt, dd');
                var optEls = [];
                for (var o = 0; o < optLike.length; o++) {
                    var t = (optLike[o].innerText || optLike[o].textContent || '').trim();
                    if (/^[A-Z][.、)）\\s]/.test(t) && t.length > 1 && t.length < 500 &&
                        optLike[o].offsetParent !== null) {
                        optEls.push(optLike[o]);
                    }
                }
                if (optEls.length >= 2) {
                    var ancestor2 = optEls[0].parentElement;
                    for (var up2 = 0; up2 < 10; up2++) {
                        if (!ancestor2 || ancestor2 === document.body) break;
                        var allIn = true;
                        for (var o2 = 0; o2 < optEls.length; o2++) {
                            if (!ancestor2.contains(optEls[o2])) { allIn = false; break; }
                        }
                        var txtLen2 = (ancestor2.innerText || ancestor2.textContent || '').length;
                        if (allIn && txtLen2 > 30) {
                            return ancestor2;
                        }
                        ancestor2 = ancestor2.parentElement;
                    }
                }
                // 策略3：选择器查找（含智慧树常用类名）
                var selectors = [
                    '.topic-item', '.topic-box', '[class*="topic-item"]', '[class*="topic-box"]',
                    '.subject-item', '.subject-box', '[class*="subject-item"]',
                    '.ques-card-box', '.ques-item', '[class*="ques-card"]', '[class*="ques-item"]',
                    '.stem-wrapper', '[class*="stem-box"]', '[class*="stem-wrapper"]',
                    '.exam-detail', '.exam-card', '.exam-item', '[class*="exam-detail"]',
                    '.question-card', '.question-item', '[class*="question-card"]', '[class*="question-item"]',
                    '.el-card__body', '.el-card', '.paper-item',
                    '.el-dialog__body', '.el-form-item__content',
                    'div[class*="card"]', 'div[class*="panel"]',
                    '[class*="exam-content"]', '[class*="question-area"]',
                    '[class*="topic-detail"]', '[class*="answer-area"]'
                ];
                for (var j = 0; j < selectors.length; j++) {
                    try {
                        var el = document.querySelector(selectors[j]);
                        if (el && el.offsetParent !== null &&
                            (el.innerText || el.textContent || '').length > 20) {
                            return el;
                        }
                    } catch(e) {}
                }
                // 策略4：取可见区域内文本最多的非 body 容器
                var best = null;
                var bestLen = 0;
                var containers = document.querySelectorAll('div, section, article, main, form');
                for (var c = 0; c < containers.length; c++) {
                    if (containers[c].offsetParent === null) continue;
                    var tag = (containers[c].tagName || '').toUpperCase();
                    if (tag === 'BODY' || tag === 'HTML') continue;
                    var txt = (containers[c].innerText || containers[c].textContent || '').trim();
                    if (txt.length > bestLen && txt.length < 10000) {
                        var hasOpt = /[A-Z][.、)）]/.test(txt);
                        if (hasOpt || bestLen === 0 || txt.length > bestLen * 2) {
                            best = containers[c];
                            bestLen = txt.length;
                        }
                    }
                }
                if (best && bestLen > 30) return best;
                // 策略5：返回 body（截图整页）
                return document.body;
            """)
            if not card:
                return ""
            img = self.screenshot_web_element(card)
            # 保存调试截图
            try:
                from pathlib import Path
                import datetime
                debug_dir = Path("debug")
                debug_dir.mkdir(exist_ok=True)
                ts = datetime.datetime.now().strftime("%H%M%S")
                img.save(str(debug_dir / f"ocr_{ts}.png"))
                logger.debug(f"OCR 截图已保存到 debug/ocr_{ts}.png")
            except Exception:
                pass
            raw = self.ocr_text(img)
            if raw and len(raw.strip()) > 20:
                logger.debug(f"OCR 卡片截图成功，原始文本 {len(raw)} 字")
            return raw
        except Exception as e:
            logger.error(f"截图 OCR 失败: {e}")
            return ""

    def _dom_text_fallback(self, driver: Any) -> str:
        """DOM 文本回退：优先从题目相关 DOM 元素提取，再回退到全页文本。"""
        import re as _re
        try:
            # 优先尝试从题目容器中提取文本
            container_text = driver.execute_script("""
                var selectors = [
                    '[class*="topic"]', '[class*="subject"]', '[class*="question"]',
                    '[class*="stem"]', '[class*="exam"]', '[class*="ques"]',
                    '.el-card__body', '.el-card', '.el-dialog__body',
                    'article', 'main', '[role="main"]'
                ];
                var best = '';
                for (var s = 0; s < selectors.length; s++) {
                    try {
                        var els = document.querySelectorAll(selectors[s]);
                        for (var e = 0; e < els.length; e++) {
                            if (els[e].offsetParent === null) continue;
                            var txt = (els[e].innerText || els[e].textContent || '').trim();
                            // 选择文本最长且包含选项标记的容器
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
                lines = container_text.split('\n')
                clean = []
                skip = [
                    r'智慧树', r'Teenity', r'暂存', r'提交作业', r'作业名称',
                    r'对应章节', r'成绩类型', r'剩余时间', r'截止时间',
                    r'题目数', r'总分数', r'说明', r'完成率', r'提示',
                    r'^\d+天', r'^\d+时分', r'第\d+部分', r'总题数',
                    r'上一题', r'下一题', r'Copyright', r'沪ICP', r'电子营业执照',
                    r'在线学堂', r'^\d+$', r'^\d+%$', r'答题后请点', r'名称\s',
                    r'试卷已提交', r'不能继续答题', r'已提交', r'保存',
                    r'^\s*$', r'^[A-Z]\s*$'
                ]
                for line in lines:
                    s = line.strip()
                    if not s or len(s) > 300:
                        continue
                    ignored = False
                    for p in skip:
                        if _re.search(p, s):
                            ignored = True
                            break
                    if not ignored:
                        clean.append(s)
                result = '\n'.join(clean)
                if len(result.strip()) >= 10:
                    return result

            # 回退：全文提取
            raw = driver.execute_script(
                "return document.body.innerText || document.body.textContent || '';"
            ) or ""
            lines = raw.split('\n')
            clean = []
            skip = [
                r'智慧树', r'Teenity', r'暂存', r'提交作业', r'作业名称',
                r'对应章节', r'成绩类型', r'剩余时间', r'截止时间',
                r'题目数', r'总分数', r'说明', r'完成率', r'提示',
                r'^\d+天', r'^\d+时分', r'第\d+部分', r'总题数',
                r'上一题', r'下一题', r'Copyright', r'沪ICP', r'电子营业执照',
                r'在线学堂', r'^\d+$', r'^\d+%$', r'答题后请点', r'名称\s',
                r'试卷已提交', r'不能继续答题', r'已提交', r'保存',
                r'^\s*$'
            ]
            for line in lines:
                s = line.strip()
                if not s or len(s) > 300:
                    continue
                ignored = False
                for p in skip:
                    if _re.search(p, s):
                        ignored = True
                        break
                if not ignored:
                    clean.append(s)
            return '\n'.join(clean)
        except Exception:
            return ""

    def _ocr_fallback(self, driver: Any) -> str:
        """回退方案：截取整个视口做 OCR。"""
        try:
            body = driver.execute_script("return document.body;")
            if not body:
                return ""
            img = self.screenshot_web_element(body)
            return self.ocr_text(img)
        except Exception as e:
            logger.error(f"OCR 回退失败: {e}")
            return ""

    def _click_exam_options(self, driver: Any, selected: List[str], qa_text: str = "") -> bool:
        """点击匹配的选项 - 只触发一次点击，防止 Vue 多重响应。"""
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
            logger.debug(f"  选项[{o['idx']}]: {o['text'][:60]}")

        def js_click(idx: int) -> bool:
            """单次点击，只触发一次，避免 Vue 收到重复事件。"""
            return driver.execute_script("""
                var targetIdx = parseInt(arguments[0]);
                var el = document.querySelector('[__opt_idx__="' + targetIdx + '"]');
                if (!el) return false;

                // 策略A: 查找包含的 input[type=radio/checkbox]，只点一次
                var inp = el.querySelector('input[type="radio"], input[type="checkbox"]');
                if (!inp) {
                    var p = el.parentElement;
                    if (p) inp = p.querySelector('input[type="radio"], input[type="checkbox"]');
                }
                if (inp) {
                    try { inp.click(); } catch(e) {}
                    return true;
                }

                // 策略B: 在标记元素附近查找所有可见 input，按索引点击
                var allInputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                var visInputs = [];
                for (var ai = 0; ai < allInputs.length; ai++) {
                    if (allInputs[ai].offsetParent !== null) visInputs.push(allInputs[ai]);
                }
                if (targetIdx < visInputs.length) {
                    try { visInputs[targetIdx].click(); } catch(e) {}
                    return true;
                }

                // 策略C: 点击标记元素本身
                try { el.click(); } catch(e) {}
                return true;
            """, str(idx))

        clicked = set()
        for ans in selected:
            ans_upper = str(ans).strip().upper()
            if not ans_upper:
                continue
            matched = False

            # 字母索引匹配 (A/B/C/D...)
            if len(ans_upper) == 1 and ans_upper[0].isalpha():
                idx = ord(ans_upper[0]) - ord('A')
                if 0 <= idx < len(opt_data) and idx not in clicked:
                    if js_click(idx):
                        clicked.add(idx)
                        logger.info(f"字母点击 {ans_upper} -> 选项[{idx}]: {opt_data[idx]['text'][:50]}")
                        matched = True

            # 文本包含匹配
            if not matched:
                for item in opt_data:
                    i = item["idx"]
                    if i in clicked:
                        continue
                    txt_u = (item["text"] or "").upper()
                    if ans_upper in txt_u or txt_u.startswith(ans_upper) or txt_u.endswith(ans_upper):
                        if js_click(i):
                            clicked.add(i)
                            logger.info(f"文本匹配 {ans_upper} -> 选项[{i}]: {item['text'][:50]}")
                            matched = True
                            break

            # 判断题匹配：对/错
            if not matched:
                tf_keywords = {
                    "对": ["对", "正确", "TRUE", "T", "是", "YES", "Y"],
                    "错": ["错", "错误", "FALSE", "F", "否", "NO", "N"],
                }
                keywords = tf_keywords.get(ans_upper, [ans_upper])
                for kw in keywords:
                    kw_u = kw.upper()
                    for item in opt_data:
                        i = item["idx"]
                        if i in clicked:
                            continue
                        item_u = (item["text"] or "").upper()
                        if kw_u in item_u or item_u.startswith(kw_u):
                            if js_click(i):
                                clicked.add(i)
                                logger.info(f"判断点击 '{ans_upper}' -> 选项[{i}]: {item['text'][:50]}")
                                matched = True
                                break
                    if matched:
                        break

            # 判断题索引回退（通常 A=错 B=对）
            if not matched:
                tf_to_idx = {"错": 0, "错误": 0, "FALSE": 0, "F": 0, "否": 0,
                             "对": 1, "正确": 1, "TRUE": 1, "T": 1, "是": 1}
                idx = tf_to_idx.get(ans_upper, -1)
                if idx >= 0 and idx < len(opt_data) and idx not in clicked:
                    if js_click(idx):
                        clicked.add(idx)
                        logger.info(f"判断索引回退 '{ans_upper}' -> 选项[{idx}]")
                        matched = True

            if not matched:
                logger.warning(f"未能匹配答案 '{ans_upper}' 到任何选项")

        # 默认保底
        if not clicked and opt_data:
            logger.warning("无选项被点击，默认点击索引 0 (A)。")
            js_click(0)
            clicked.add(0)

        # 验证选中状态
        if clicked:
            sleep(0.6)
            verified = driver.execute_script("""
                var checked = document.querySelectorAll(
                    'input[type="radio"]:checked, input[type="checkbox"]:checked'
                );
                var activeEls = document.querySelectorAll(
                    '.el-radio.is-checked, .el-checkbox.is-checked, ' +
                    '[class*="is-checked"], [class*="is-active"], ' +
                    '[class*="checked"], [class*="active"], ' +
                    '[aria-checked="true"]'
                );
                return {inputChecked: checked.length, activeEls: activeEls.length};
            """)
            logger.info(f"选中验证: input选中={verified.get('inputChecked',0)}, active元素={verified.get('activeEls',0)}")

        return True

    def _click_options_fallback(self, driver: Any, selected: List[str]) -> bool:
        """通用选项查找与点击（当标记方式失败时使用）。"""
        options = driver.execute_script("""
            var all = [];
            // 优先查找实际的 radio/checkbox input（最可靠）
            var inputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
            if (inputs.length >= 2) {
                for (var i = 0; i < inputs.length; i++) {
                    all.push(inputs[i]);
                }
            }
            // 回退：查找选项文本标签
            if (all.length === 0) {
                var els = document.querySelectorAll('div, li, span, label');
                for (var j = 0; j < els.length; j++) {
                    var t = (els[j].innerText || els[j].textContent || '').trim();
                    if (/^[A-Z][.、)\\s:：]/.test(t) && t.length < 300) {
                        all.push(els[j]);
                    }
                }
            }
            return all;
        """)

        if not options:
            logger.error("回退方案也未找到选项。")
            return False

        logger.info(f"回退方案找到 {len(options)} 个选项")

        def click_opt(idx):
            driver.execute_script("""
                var inputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                var idx = arguments[0];
                if (idx < inputs.length) {
                    var inp = inputs[idx];
                    try { inp.focus(); } catch(e) {}
                    try { inp.click(); } catch(e) {}
                    try { inp.checked = true; } catch(e) {}
                    try { inp.dispatchEvent(new Event('change', {bubbles: true})); } catch(e) {}
                    var label = inp.closest('label');
                    if (label) { try { label.click(); } catch(e) {} }
                    return;
                }
                // 回退：点击标记的文本元素
                var all = arguments[1];
                if (all && idx < all.length) {
                    try { all[idx].click(); } catch(e) {}
                }
            """, idx, options)

        clicked = set()
        for ans in selected:
            ans_upper = str(ans).strip().upper()
            if ans_upper and len(ans_upper) == 1 and ans_upper[0].isalpha():
                idx = ord(ans_upper[0]) - ord('A')
                if 0 <= idx < len(options) and idx not in clicked:
                    click_opt(idx)
                    clicked.add(idx)
                    logger.info(f"回退点击选项 {ans_upper}")
                    continue
            # 文本匹配
            for i, el in enumerate(options):
                if i in clicked:
                    continue
                txt = ""
                try:
                    txt = driver.execute_script("return arguments[0].innerText || arguments[0].textContent || '';", el) or ""
                except Exception:
                    pass
                if ans_upper in txt.upper():
                    click_opt(i)
                    clicked.add(i)
                    break

        if not clicked and options:
            click_opt(0)
        return True

    # 对指定元素图片进行 OCR 识别，并将识别结果拼成字符串交给 LLM 解答。
    def solve_answers_from_image(self, element: Any = None, save_crop_path: Optional[str] = None, driver: Any = None) -> bool:
        # 校验 driver 并定位题目容器元素
        if driver is None and element is None:
            logger.error("solve_answers_from_image 需要传入 driver 或已定位的元素")
            return False
        try:
            ques_box = element or driver.execute_script(
                "return document.querySelector('div.ques .item.ques-card-box');"
            )
        except Exception as e:
            logger.error(f"查询题目容器失败: {e}")
            ques_box = None
        if not ques_box:
            logger.error("未找到题目容器 div.ques .item.ques-card-box")
            return False
    
        # 截取元素图片
        img = self.screenshot_web_element(ques_box, save_crop_path)
    
        # 对元素图片进行 OCR，得到题目与选项文本
        try:
            qa_text = self.ocr_text(img)
        except Exception as e:
            logger.error(f"OCR处理失败: {e}")
            qa_text = ""
        logger.debug(f"OCR提取题目与选项：{qa_text}")
        
        # 交给 LLM 获取答案列表
        selected: List[str] = []
        try:
            result = self.llm.answer_question(qa_text)
            logger.debug(f"LLM返回: {result}")
            if isinstance(result, dict):
                sel = result.get("selected")
                if isinstance(sel, list):
                    selected = [str(s).strip() for s in sel]
        except Exception as e:
            logger.error(f"LLM解答失败: {e}")
            selected = []
        
        # 若提供 driver，则执行页面选项定位与点击，并提交
        if driver:
            try:
                # 获取所有选项元素
                options = driver.execute_script(
                    "return Array.from(document.querySelectorAll('.ques .item.ques-card-box .options .option'));"
                )
                if not options:
                    logger.error("未找到选项元素 .ques .item.ques-card-box .options .option")
                logger.debug(f"页面选项元素数量: {len(options) if options else 0}")
                
                # 预取每个选项文本（便于匹配判断题）
                opt_texts = []
                for el in options or []:
                    try:
                        txt = driver.execute_script(
                            "return (arguments[0].innerText||arguments[0].textContent||'').trim();",
                            el,
                        ) or ""
                    except Exception:
                        txt = ""
                    opt_texts.append(txt)
                logger.debug(f"选项文本列表: {opt_texts}")
                
                # 点击选项
                def click_opt(el):
                    try:
                        driver.execute_script("arguments[0].click();", el)
                    except Exception:
                        try:
                            el.click()
                        except Exception as e2:
                            logger.warning(f"选项点击失败: {e2}")
        
                def match_true_false(ans: str):
                    a = str(ans).strip()
                    if a in ("对","正确","TRUE","T","YES","Y","是"):
                        for i, t in enumerate(opt_texts):
                            if "对" in t or "正确" in t:
                                return i
                    if a in ("错","错误","FALSE","F","NO","N","否"):
                        for i, t in enumerate(opt_texts):
                            if "错" in t or "错误" in t:
                                return i
                    return None
        
                # 依据提示词：优先按字母选项；判断题则匹配“对/错”；无法判断时也要选择一个
                normalized = []
                for s in selected or []:
                    if not s:
                        continue
                    s2 = str(s).strip()
                    # 提示词要求字母返回，统一转大写
                    normalized.append(s2.upper())
        
                indices_to_click = []
                for ans in normalized:
                    # 字母选项（A/B/C/...）
                    if ans and ans[0].isalpha():
                        idx = ord(ans[0]) - ord('A')
                        if options and 0 <= idx < len(options):
                            indices_to_click.append(idx)
                            logger.info(f"选择字母答案: {ans} -> 选项索引 {idx}")
                            continue
                    # 判断题匹配
                    idx_tf = match_true_false(ans)
                    if idx_tf is not None:
                        indices_to_click.append(idx_tf)
                        logger.info(f"选择判断题答案: {ans} -> 选项索引 {idx_tf}")
        
                # 若仍未有任何可点击索引，按提示词“无法判断则返回一个你认为对的选择”，选择第一个
                if options and not indices_to_click:
                    indices_to_click = [0]
                    logger.info(f"未能从答案列表匹配到选项，按提示词策略选择第一个选项: {opt_texts[0]}")
        
                # 去重并按索引升序点击（避免重复点击）
                for idx in sorted(set(indices_to_click)):
                    try:
                        click_opt(options[idx])
                    except Exception as e:
                        logger.warning(f"点击选项索引 {idx} 失败: {e}")
        
                # 提交答案
                submit = driver.execute_script(
                    "return document.querySelector('div.question-body .submit-footer .submit-btn span.submits');"
                )
                if submit:
                    try:
                        driver.execute_script("arguments[0].click();", submit)
                        logger.info("已点击提交按钮")
                    except Exception:
                        try:
                            submit.click()
                            logger.info("已点击提交按钮")
                        except Exception as e2:
                            logger.warning(f"提交按钮点击失败: {e2}")
                else:
                    logger.warning("未找到提交按钮")
            except Exception as e:
                logger.error(f"页面答题流程失败: {e}")

            sleep(2)
            
            # HACK: 关闭页面
            close_box = driver.execute_script(
                """
                var root = document.querySelector('div.ai-test-question-wrapper');
                if (!root) return null;
                return root.querySelector('.header-box .close-box')
                    || root.querySelector('.header-box [class*="close"]')
                    || root.querySelector('.header-box .right-box .close-box')
                    || root.querySelector('.header-box .close');
                """
            )
            if close_box:
                try:
                    driver.execute_script(
                        """
                        var el = arguments[0];
                        try { el.scrollIntoView({block:'center', inline:'center'}); } catch(e){}
                        try { el.click(); } catch(e){}
                        try {
                            var rect = el.getBoundingClientRect();
                            var opts = {view: window, bubbles: true, cancelable: true, clientX: rect.left + rect.width/2, clientY: rect.top + rect.height/2};
                            ['pointerdown','mousedown','mouseup','click'].forEach(function(t){ try { el.dispatchEvent(new MouseEvent(t, opts)); } catch(e){} });
                        } catch(e) {}
                        """,
                        close_box,
                    )
                    logger.info("已触发关闭按钮事件")
                except Exception as e:
                    logger.warning(f"关闭按钮事件派发失败: {e}")

                # 验证是否关闭
                try:
                    closed = driver.execute_script(
                        "var r=document.querySelector('div.ai-test-question-wrapper'); return !r || r.style.display==='none' || r.offsetParent===null;"
                    )
                except Exception:
                    closed = False
                if not closed:
                    close_box.click()
            else:
                logger.error("未找到关闭按钮")
            return True
        return False