# 更新了历记录投喂机制，防止token爆炸。
# 优化了可能出现的刷新问题
import streamlit as st
import requests
from docx import Document
import pypdf
import re
import json

# ==========================================
# 1. 页面基本配置
# ==========================================
st.set_page_config(page_title="ERP智能选型系统", page_icon="🤖", layout="wide")

st.title("🤖 ERP 智能选型顾问 ")
st.caption("基于 DeepSeek 驱动的企业招标书分析与 RFP 矩阵自动生成系统")

# ==========================================
# 2. 初始化核心底座（API与内置知识库）
# ==========================================
api_key = st.secrets["DEEPSEEK_API_KEY"]
api_url = "https://api.deepseek.com/chat/completions"

# 提前投喂给 AI 的标准企业级数据（防止幻觉）
erp_knowledge_base = """
【以下是供你参考的 ERP 官方产品知识库，请严格基于此信息进行匹配打分，不得凭空捏造】：
1. SAP S/4HANA (Cloud):
   - 优势：全球财务多准则、多币种合并绝对标杆；供应链与跨国制造流程极其严密；全球合规性最高。
   - 劣势：实施周期极长（通常6个月以上），极度依赖外部高价顾问，商务成本极其昂贵（百万至千万级）。
   - 适用：大型跨国集团、重资产制造业、预算充足的出海头部企业。

2. Oracle NetSuite:
   - 优势：原生云架构（SaaS），上线快（2-3个月）；跨境电商与轻量化供应链支持好；多语言多税制合规能力极强。
   - 劣势：对大型复杂工厂的精细化车间生产（如复杂的BOM、车间排产）支持相对单薄；订阅费按年续缴。
   - 适用：中型成长型企业、出海贸易/跨境电商、轻资产运营企业、预算在 80-200 万之间。

3. 金蝶云星空 (Kingdee):
   - 优势：国内财务与税务政策响应极快；本土化制造与仓储生态极其成熟；性价比极高，实施轻量。
   - 劣势：海外本地化税制和多语种合规能力正在拓展中，对于纯海外本土化运营的支撑弱于国际巨头。
   - 适用：国内中大型制造与民营企业、看重预算控制与国内供应链落地的企业、预算在 30-100 万之间。
"""

system_content = f"""你是一位资深的企业数字化转型专家、CIO咨询顾问与 ERP 选型专家。
请深度分析用户提供的【企业招标书/需求文本】，结合下方提供的【ERP知识库】，为用户自动生成极具行业专业度的 RFP 对比矩阵和最终选型推荐。

{erp_knowledge_base}

【工作流与输出规范】：
你必须且只能输出以下三个部分，并严格使用清晰的 Markdown 格式：

### 1. 企业核心需求与动态权重分析
- 精准提炼招标书中的痛点（如财务合规、供应链、预算瓶颈、出海合规等），并给出数字化视角的权重分配理由。

### 2. RFP 对比矩阵（严格使用表格形式，必须包含评分理由）
- 表格横轴必须为：评估维度(权重)、SAP S/4HANA、Oracle NetSuite、金蝶云星空、选型打分理由与核心依据。
所有维度评分采用十分制，保留一位小数，加权综合得分 = 各维度得分 × 对应权重之和，最终也以十分制呈现。
- 表格纵轴必须为：财务能力、供应链管理、全球化合规、商务预算控制、加权综合得分.
- 【严禁敷衍】：请在“选型打分理由与核心依据”一列中，针对每一个维度，结合各家产品的优劣势与标书需求的契合度，给出犀利、专业的定量或定性分析理由。
- 【关于加权综合得分的严硬性规定】：
  在计算最终一行“加权综合得分”时，请一步一步来。你必须在心中严格执行：
  加权得分 = (财务得分 × 财务权重) + (供应链得分 × 供应链权重) + (合规得分 × 合规权重) + (预算得分 × 预算权重)
  确保四舍五入保留到小数点后两位。严禁随意胡编一个总分！

### 3. 智能体最终专家级选型推荐
- 给出明确的一体化建设路线建议，包括推荐系统、预估实施周期、核心风险提示。
---
"""

# 初始化历史纪录与状态
if "history" not in st.session_state:
    st.session_state.history = []

if "current_report" not in st.session_state:
    st.session_state.current_report = None

if "file_processed" not in st.session_state:
    st.session_state.file_processed = False

# ==========================================
# 3. 网页侧边栏
# ==========================================
with st.sidebar:
    st.header("⚙️ ERP 智能选型系统")
    st.subheader("朗博文组倾情打造")
    st.success("🟢 DeepSeek-chat 模型已连接")
    st.info("📚 行业知识库已挂载完成")
    st.markdown("""
    **已覆盖系统：**
    - SAP S/4HANA
    - Oracle NetSuite
    - 金蝶云星空
    """)
    
    if st.button("🔄 清空对话历史", use_container_width=True):
        st.session_state.history = []
        st.session_state.current_report = None
        st.session_state.file_processed = False
        if "last_file_key" in st.session_state:
            del st.session_state.last_file_key
        st.rerun()

    if st.session_state.current_report:
        st.write("---")
        st.markdown("### 📄 报告导出面板")
        st.download_button(
            label="📥 一键导出当前选型报告 (MD)",
            data=st.session_state.current_report,
            file_name="企业ERP选型智能分析报告.md",
            mime="text/markdown",
            use_container_width=True
        )

# ==========================================
# 4. 渲染网页历史聊天流
# ==========================================
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "caption" in msg:
            st.caption(msg["caption"])


# ==========================================
# 5. 核心交互流（固定于底部）
# ==========================================
with st.bottom:
    uploaded_file = st.file_uploader("📁 上传企业招标书/需求文档 (支持 .txt, .docx, .pdf)", type=["txt", "docx", "pdf"])
    
    if uploaded_file:
        current_file_key = f"{uploaded_file.name}_{uploaded_file.size}"
        if "last_file_key" not in st.session_state or st.session_state.last_file_key != current_file_key:
            st.session_state.last_file_key = current_file_key
            st.session_state.file_processed = False

    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            label="补充说明",
            placeholder="在此处输入补充说明或日常对话，敲回车或点击右侧按钮触发...",
            label_visibility="collapsed"
        )
        
    with col2:
        is_disabled = (uploaded_file is None and not user_input.strip())
        btn_clicked = st.button("🚀 开始分析", use_container_width=True, disabled=is_disabled)
        
    start_analysis = btn_clicked or (user_input.strip() != "")

# --- 🛠️ 步骤 A：解析文件 ---
file_context = ""
if uploaded_file is not None and not st.session_state.file_processed:
    try:
        if uploaded_file.name.endswith(".txt"):
            file_context = uploaded_file.read().decode("utf-8")
        elif uploaded_file.name.endswith(".docx"):
            doc = Document(uploaded_file)
            file_context = "\n".join([para.text for para in doc.paragraphs])
        elif uploaded_file.name.endswith(".pdf"):
            pdf_reader = pypdf.PdfReader(uploaded_file)
            file_context = "\n".join([page.extract_text() for page in pdf_reader.pages])
    except Exception as e:
        st.error(f"❌ 文件解析失败: {e}")

# --- 🛠️ 步骤 B：构建当前轮次的请求 Prompt ---
trigger_api = False
final_prompt = ""
display_text = ""
display_caption = None

if start_analysis:
    text_hint = user_input.strip()
    
    if file_context: # 包含新文件上载的情境
        if text_hint:
            final_prompt = f"【用户附加说明】：{text_hint}\n\n【上传的文档内容如下】：\n{file_context}"
            display_text = text_hint
        else:
            final_prompt = f"以下是用户上传的招标书文件内容：\n\n{file_context}"
            display_text = f"📄 分析上传文件：{uploaded_file.name}"
        display_caption = f"📁 已同步关联上传文件：{uploaded_file.name}"
        trigger_api = True
    elif text_hint: # 纯文字情境（可能为后续追问）
        final_prompt = text_hint
        display_text = text_hint
        trigger_api = True

# --- 🛠️ 步骤 C：核心调用与路由流 ---
if trigger_api and final_prompt:
    
    # 在聊天流里即时渲染用户当前输入
    with st.chat_message("user"):
        st.markdown(display_text)
        if display_caption:
            st.caption(display_caption)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # 意图识别
    routing_messages = [
        {
            "role": "system", 
            "content": (
                "你是一个极其严格的意图识别助手。\n"
                "用户如果发送了日常问候、代码修改、普通技术问答、或者针对已有报告的零散追问，请输出：[INTENT_A]\n"
                "用户如果上传了全新的招标书、提供了企业具体的全套ERP痛点、预算要求，需要重新生成完整大报告，请输出：[INTENT_B]\n"
                "请仅输出标签本身，严禁包含任何其他文字、标点、解释或空格。"
            )
        },
        {"role": "user", "content": final_prompt[:2000]} # 截取前两千字做意图识别足矣，防大文件超时
    ]
    
    raw_intent = "[INTENT_A]"
    try:
        route_response = requests.post(api_url, headers=headers, json={"model": "deepseek-chat", "messages": routing_messages, "stream": False}, timeout=10)
        raw_intent = route_response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        pass 

    # 🎯 修复解决问题3：利用正则表达式做前缀/后缀剥离，精准提取标签
    intent_match = re.search(r"\[INTENT_[A-B]\]", raw_intent)
    intent = intent_match.group(0) if intent_match else "[INTENT_A]"

    # 🎯 修复解决问题1：上下文机制隔离与滚动截断
    # 清洗历史记忆，防止历史中巨大的“旧标书文本”反复发送造成体积爆炸
    cleaned_history = []
    for h in st.session_state.history[-6:]: # 只保留最近3轮精简对话作为上下文
        cleaned_history.append({"role": h["role"], "content": h["content"][:1000]}) # 截断预防

    if intent == "[INTENT_B]":
        loading_text = "检测到全新的 ERP 选型需求，正在动态计算 RFP 矩阵..."
        current_messages = [{"role": "system", "content": system_content}] + cleaned_history + [{"role": "user", "content": final_prompt}]
    else:
        loading_text = "智能体正在思考回复..."
        chat_system_content = (
            "你是一个专业的企业数字化与 AI 技术顾问。你目前处于【技术顾问/轻量协作】模式。\n"
            "如果用户在向你追问刚才的选型报告，请直接基于记忆给出解答。如果没有，请进行正常技术日常交流。请保持严谨专业。"
        )
        current_messages = [{"role": "system", "content": chat_system_content}] + cleaned_history + [{"role": "user", "content": final_prompt}]

    data = {"model": "deepseek-chat", "messages": current_messages, "stream": True}

    with st.chat_message("assistant"):
        placeholder = st.empty()
        
        with placeholder.container():
            with st.spinner(loading_text):
                try:
                    response = requests.post(api_url, headers=headers, json=data, stream=True)
                    response.raise_for_status()
                    
                    def response_generator():
                        full_reply = ""
                        for line in response.iter_lines():
                            if line:
                                line_str = line.decode("utf-8")
                                if line_str.startswith("data: "):
                                    chunk_data = line_str[6:]
                                    if chunk_data.strip() == "[DONE]":
                                        break
                                    try:
                                        chunk_json = json.loads(chunk_data)
                                        delta = chunk_json['choices'][0]['delta'].get('content', '')
                                        full_reply += delta
                                        yield delta
                                    except:
                                        pass
                    
                    # 🎯 修复解决问题2：完美流式打字机输出
                    ai_reply = st.write_stream(response_generator())
                    
                    # 将精简后的记录归档进状态，避免历史污染
                    user_archive = {"role": "user", "content": display_text}
                    if display_caption:
                        user_archive["caption"] = display_caption
                    st.session_state.history.append(user_archive)
                    st.session_state.history.append({"role": "assistant", "content": ai_reply})
                    
                    if intent == "[INTENT_B]":
                        st.session_state.current_report = ai_reply
                        
                    if uploaded_file:
                        st.session_state.file_processed = True
                        
                except Exception as e:
                    ai_reply = f"❌ 运行出错：{e}"
                    st.error(ai_reply)
        
        # 如果是新生成的大报告，刷新页面以立刻将报告同步至侧边栏下载按钮
        if intent == "[INTENT_B]" and "❌ 运行出错" not in ai_reply:
            st.rerun()
