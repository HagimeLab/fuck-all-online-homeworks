# -*- coding: utf-8 -*-
"""
平台配置模块

定义不同学习平台的页面结构差异（登录域名、选项类名、按钮选择器等）。
新增平台时在此添加配置即可，无需修改业务逻辑代码。
"""

from typing import Dict, Any


class PlatformConfig:
    """平台配置基类"""

    # 平台标识
    NAME: str = ""

    # 登录页域名提示（用于判断是否需要登录）
    LOGIN_DOMAIN_HINT: str = ""

    # Cookie 基础域名
    COOKIE_BASE_URL: str = ""

    # 登录页二维码域名
    LOGIN_QR_DOMAIN: str = ""

    # 答题页关键词（用于检测考试结束）
    EXAM_FINISHED_KEYWORDS: list = []

    # 开始答题按钮关键词
    START_BTN_KEYWORDS: list = []

    # 下一题按钮关键词
    NEXT_BTN_KEYWORDS: list = []

    # 交卷按钮关键词
    SUBMIT_BTN_KEYWORDS: list = []

    # 确定/确认按钮关键词
    CONFIRM_BTN_KEYWORDS: list = []

    # 题目卡片选择器
    CARD_SELECTORS: list = []

    # 选项元素选择器
    OPTION_SELECTORS: list = []

    # 题目容器选择器
    QUESTION_CONTAINER_SELECTORS: list = []

    # 下一题按钮已知类名
    NEXT_BTN_KNOWN_CLASSES: list = []

    # 登录页"二维码登录"标签关键词
    QR_LOGIN_TAB_KEYWORDS: list = []

    # 需要切换到 iframe 的类名（学习通某些页面在 iframe 内）
    IFRAME_CLASS: str = ""

    # 翻题模式：button=点击按钮翻题，scroll=滚动翻题
    NAV_MODE: str = "button"

    # 选项点击后需要触发的额外事件（学习通通常需要）
    NEED_CHANGE_EVENT: bool = True

    # 选项元素中 radio/checkbox 的类名
    RADIO_CLASS: str = ""
    CHECKBOX_CLASS: str = ""

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        return {
            "name": cls.NAME,
            "login_domain_hint": cls.LOGIN_DOMAIN_HINT,
            "cookie_base_url": cls.COOKIE_BASE_URL,
            "login_qr_domain": cls.LOGIN_QR_DOMAIN,
            "exam_finished_keywords": cls.EXAM_FINISHED_KEYWORDS,
            "start_btn_keywords": cls.START_BTN_KEYWORDS,
            "next_btn_keywords": cls.NEXT_BTN_KEYWORDS,
            "submit_btn_keywords": cls.SUBMIT_BTN_KEYWORDS,
            "confirm_btn_keywords": cls.CONFIRM_BTN_KEYWORDS,
            "card_selectors": cls.CARD_SELECTORS,
            "option_selectors": cls.OPTION_SELECTORS,
            "question_container_selectors": cls.QUESTION_CONTAINER_SELECTORS,
            "next_btn_known_classes": cls.NEXT_BTN_KNOWN_CLASSES,
            "qr_login_tab_keywords": cls.QR_LOGIN_TAB_KEYWORDS,
            "iframe_class": cls.IFRAME_CLASS,
            "need_change_event": cls.NEED_CHANGE_EVENT,
            "radio_class": cls.RADIO_CLASS,
            "checkbox_class": cls.CHECKBOX_CLASS,
            "nav_mode": cls.NAV_MODE,
        }


class ZhiHuishuConfig(PlatformConfig):
    """智慧树平台配置"""

    NAME = "智慧树"
    LOGIN_DOMAIN_HINT = "passport.zhihuishu.com"
    COOKIE_BASE_URL = "https://onlineweb.zhihuishu.com/"
    LOGIN_QR_DOMAIN = "passport.zhihuishu.com"
    EXAM_FINISHED_KEYWORDS = [
        "提交成功", "交卷成功", "考试结束", "答题完成",
        "试卷已提交", "已提交", "交卷完成", "恭喜您完成",
        "不能继续答题", "无需再次答题", "您已完成",
    ]
    START_BTN_KEYWORDS = ["开始答题", "开始考试", "进入考试", "开始作答", "进入答题"]
    NEXT_BTN_KEYWORDS = ["下一题", "下一頁"]
    SUBMIT_BTN_KEYWORDS = ["交卷", "提交试卷", "提交"]
    CONFIRM_BTN_KEYWORDS = ["确定", "确认", "是"]
    CARD_SELECTORS = [
        ".question-card", ".exam-card", ".topic-card",
        "[class*='question']", "[class*='topic-detail']",
        ".el-card", ".paper-item", ".exam-item",
        ".topic-item", ".topic-box", ".subject-box",
        ".ques-card-box", ".ques-item", "[class*='ques']",
        "[class*='stem-box']", "[class*='subject']",
        ".el-dialog__body", "[class*='exam-area']",
    ]
    OPTION_SELECTORS = [
        ".option", ".option-item", ".choice-item", "li[class*='option']",
        "div[class*='option-item']", ".options>li", ".options>div",
        ".answer-option", "[class*='exam-option']",
        ".el-radio", "label.el-radio", ".radio-item",
        ".check-item", ".radio-wrap", "[class*='option-wrap']",
        "[class*='topic-option']", "[class*='option-box']",
        ".answer-item", "[class*='answer-item']",
    ]
    QUESTION_CONTAINER_SELECTORS = [
        "[class*='topic']", "[class*='subject']", "[class*='question']",
        "[class*='stem']", "[class*='exam']", ".el-card__body",
    ]
    NEXT_BTN_KNOWN_CLASSES = [
        ".Topicswitchingbtn", ".Topicswitchingbtn-gray",
        ".Nextbtndiv span", "[class*='Topic']span",
        ".next-btn", ".nextBtn", ".next-question",
    ]
    QR_LOGIN_TAB_KEYWORDS = ["二维码", "扫码"]
    IFRAME_CLASS = ""
    NEED_CHANGE_EVENT = True
    RADIO_CLASS = ".el-radio"
    CHECKBOX_CLASS = ".el-checkbox"


class ChaoXingConfig(PlatformConfig):
    """超星学习通/尔雅平台配置"""

    NAME = "学习通"
    LOGIN_DOMAIN_HINT = "passport2.chaoxing.com"
    COOKIE_BASE_URL = "https://mooc1-ch1.chaoxing.com/"
    LOGIN_QR_DOMAIN = "passport2.chaoxing.com"
    EXAM_FINISHED_KEYWORDS = [
        "交卷成功", "已交卷", "已完成", "exam-end", "exam_end",
        "提交成功", "考试结束", "答题完成", "试卷已提交",
        "不能继续答题", "无需再次答题", "您已完成",
    ]
    START_BTN_KEYWORDS = ["开始考试", "开始答题", "进入考试", "进入答题"]
    NEXT_BTN_KEYWORDS = ["下一题", "next", "next_btn", "domUtils__nextQuestion"]
    SUBMIT_BTN_KEYWORDS = ["交卷", "tijiao", "tijiao_exam_btn", "tijiao_exam", "tijiao_exam_btn", "tijiaoBtn"]
    CONFIRM_BTN_KEYWORDS = ["确定", "确认", "是", "ok"]
    CARD_SELECTORS = [
        ".stui__exam-question", ".stui__homework-item",
        "[data-type='choice']", ".choice-question",
        ".stui__exam-paper", ".stui__question",
        "[class*='exam-question']", "[class*='homework-item']",
        ".stui__form-radio", ".stui__form-checkbox",
        ".stui__radio-group", ".stui__checkbox-group",
        ".stui__radio", ".stui__checkbox",
        ".stui__input-radio", ".stui__input-checkbox",
    ]
    OPTION_SELECTORS = [
        "div[role='radio']", "div[role='checkbox']",
        "div[class*='answerBg']",
        ".g-checkbox", ".ckeCK",
        ".stui__radio", ".stui__input-radio", ".stui__form-radio",
        ".stui__checkbox", ".stui__input-checkbox", ".stui__form-checkbox",
        ".stui__radio-group", ".stui__checkbox-group",
        "[class*='stui__radio']", "[class*='stui__checkbox']",
        "[class*='stui__option']", "[class*='stui__answer']",
        ".option-item", ".choice-item", "[class*='option']",
    ]
    QUESTION_CONTAINER_SELECTORS = [
        "[class*='stui__']", "[class*='exam-question']",
        "[class*='homework-item']", ".stui__form",
        "[class*='question']", "[class*='topic']",
        ".el-card__body", ".el-card", ".el-dialog__body",
    ]
    NEXT_BTN_KNOWN_CLASSES = [
        ".next_btn", ".domUtils__nextQuestion",
        ".domUtils_nextBtn", ".btn-next",
    ]
    QR_LOGIN_TAB_KEYWORDS = ["二维码", "扫码", "扫码登录", "二维码登录"]
    IFRAME_CLASS = ""
    NEED_CHANGE_EVENT = True
    RADIO_CLASS = ".g-checkbox"
    CHECKBOX_CLASS = ".ckeCK"
    NAV_MODE = "tab"  # 学习通用右侧题号列表切换题目


# 平台配置映射表
PLATFORM_MAP = {
    "zhihuishu": ZhiHuishuConfig,
    "chaoxing": ChaoXingConfig,
}

# 用户友好的平台名称映射
PLATFORM_NAMES = {
    "zhihuishu": "智慧树",
    "chaoxing": "学习通（超星尔雅）",
}


def get_platform_config(platform: str) -> type[PlatformConfig]:
    """
    根据平台标识获取配置类。

    Args:
        platform: 平台标识，如 "zhihuishu" 或 "chaoxing"

    Returns:
        对应的 PlatformConfig 子类

    Raises:
        ValueError: 未知平台标识
    """
    config_cls = PLATFORM_MAP.get(platform)
    if config_cls is None:
        available = ", ".join(PLATFORM_NAMES.keys())
        raise ValueError(f"未知平台: {platform}。可用平台: {available}")
    return config_cls
