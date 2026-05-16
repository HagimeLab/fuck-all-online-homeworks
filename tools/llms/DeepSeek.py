import json
import re
from typing import List, Dict, Any
from openai import OpenAI
from loguru import logger
from config.JsonLoadConfig import get_llm_deepseek_config


# DeepSeek 配置
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"


class DeepSeek:
    def __init__(
        self,
    ):
        # 统一从 JsonLoadConfig 读取
        ds = get_llm_deepseek_config()
        self.api_key = ds.get("api_key")
        if not self.api_key or self.api_key == "YOUR_API_KEY":
            logger.error("DeepSeek API 密钥未配置")
            raise RuntimeError("请设置环境变量 DEEPSEEK_API_KEY 或在 config.json 的 llm.deepseek.api_key 写入真实的密钥。")
        self.client = OpenAI(api_key=self.api_key, base_url=ds.get("base_url") or DEEPSEEK_BASE_URL)
        self.model = ds.get("model") or DEEPSEEK_MODEL
        logger.info(f"DeepSeek 初始化完成，模型：{self.model}")

    def answer_question(self, qa_text: str) -> Dict[str, Any]:
        """
        直接把题目与选项的原始文本交给模型，不做任何预处理/分离。
        要求模型只返回严格 JSON：{"selected": ["A"]}。
        """
        if not qa_text:
            logger.error("题目不能为空")
            raise ValueError("qa_text 不能为空")

        sys_prompt = (
            "你是专业的答题助手。我会把题目和选项一起给你，你需要选出正确答案。\n"
            "规则：\n"
            "1. 单选题：返回 {\"selected\": [\"A\"]}（字母对应选项）\n"
            "2. 多选题：返回 {\"selected\": [\"A\", \"C\"]}（多个字母）\n"
            "3. 判断题：返回 {\"selected\": [\"对\"]} 或 {\"selected\": [\"错\"]}\n"
            "4. 如果不确定，也必须给出你认为最可能的答案\n"
            "5. 只返回纯 JSON，不要有任何额外文字、解释或代码块标记\n"
            "题目和选项文本中可能混有页面UI文字（如题号、分数字样），请自动忽略，只关注题目内容和选项。"
        )
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": qa_text},
        ]

        # 截断过长文本，防止 token 超限
        max_len = 3000
        if len(qa_text) > max_len:
            logger.warning(f"题目文本过长 ({len(qa_text)} 字符)，截断到 {max_len}")
            qa_text = qa_text[:max_len]

        logger.info(f"问题：{qa_text}")
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            logger.info(f"DeepSeek 原始回复：{resp}")
            content = resp.choices[0].message.content if resp and resp.choices else ""
            logger.info(f"DeepSeek 回复内容：{content}")
            return self.parse_content(content)
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            return {"selected": ["A"], "raw": "", "error": str(e)}

    def parse_content(self, content: str) -> Dict[str, Any]:
        """
        仅解析模型返回的严格 JSON，提取 selected 数组。
        - 允许答案元素为选项字母（统一转为大写）、中文“对/错”、或选项原文；
        - 若解析不到有效 selected，则返回空数组。
        """
        raw = content or ""
        cleaned = raw.strip()
        cleaned = re.sub(r"^```json\s*|\s*```$", "", cleaned)
        cleaned = re.sub(r"^```\s*|\s*```$", "", cleaned)

        result: Dict[str, Any] = {"selected": [], "raw": raw}
        try:
            data = json.loads(cleaned)
            sel = data.get("selected")
            if isinstance(sel, list):
                selected: List[str] = []
                for s in sel:
                    if s is None:
                        continue
                    token = str(s).strip()
                    if not token:
                        continue
                    # 字母统一大写，其余保留原样（含“对/错”和选项原文）
                    if re.fullmatch(r"[A-Za-z]", token):
                        token = token.upper()
                    selected.append(token)
                result["selected"] = selected
        except Exception:
            pass
        logger.debug(f"DeepSeek.parse_content: result={result}")
        return result


def get_client() -> DeepSeek:
    """
    获取一个 DeepSeek 客户端实例。
    """
    return DeepSeek()


if __name__ == "__main__":
    # 示例：单一字符串输入
    client = get_client()
    qa_text = (
        "执行以int a=10;printf(“%d”,a++);后的输出结果和a的值是（ ）。"
        "A. 10和11"
        "B. 11和10"
        "C. 10和10"
        "D. 11和11"
    )
    result = client.answer_question(qa_text)
    
    print(json.dumps({"selected": result["selected"]}, ensure_ascii=False)) # 模型返回的 JSON 字符串
    print(result["raw"])    # 原始文本
    print(result["selected"])   # 解析后的选项字母数组
    print(result["selected"][0]) # 第一个选项字母
