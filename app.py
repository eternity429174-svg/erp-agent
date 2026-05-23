import streamlit as st
import requests

# ==========================================
# 1. 页面基本配置（告别黑框，配置精美网页）
# ==========================================
st.set_page_config(page_title="ERP智能选型系统", page_icon="🤖", layout="wide")

st.title("🤖 ERP 智能选型顾问 Agent")
st.caption("基于 DeepSeek 驱动的企业招标书分析与 RFP 矩阵自动生成系统")

# ==========================================
# 2. 初始化核心底座（API与内置知识库）
# ==========================================
api_key = "sk-a246cbcba4424d2682ca9f6d1c44d813"
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

# 你的系统提示词，用来约束大模型的业务行为和输出格式
system_content = f"""你是一位资深的企业数字化转型专家与 ERP 选型顾问。
请分析用户提供的【企业招标书/需求文本】，结合下方提供的【ERP知识库】，为用户自动生成 RFP 对比矩阵和选型推荐。

{erp_knowledge_base}

【工作流与输出规范】：
你必须且只能输出以下三个部分，并严格使用 Markdown 格式：
### 1. 企业核心需求与动态权重分析
### 2. RFP 对比矩阵（严格使用表格形式）
横轴为：评估维度(权重)、SAP S/4HANA、Oracle NetSuite、金蝶云星空。
纵轴为：财务、供应链、全球化合规、商务预算、加权综合得分。
### 3. 智能体最终选型推荐
---
"""

# 用 Streamlit 的会话状态（session_state）来管理对话历史，代替你原本的 history 列表
# 这样即便网页刷新，记忆也不会丢失
if "history" not in st.session_state:
    st.session_state.history = [{"role": "system", "content": system_content}]

# ==========================================
# 3. 网页侧边栏（展示专业感）
# ==========================================
with st.sidebar:
    st.header("⚙️ 智能体底座配置")
    st.success("🟢 DeepSeek-chat 模型已连接")
    st.info("📚 行业知识库已挂载完成")
    st.markdown("""
    **已覆盖系统：**
    - SAP S/4HANA
    - Oracle NetSuite
    - 金蝶云星空
    """)
    if st.button("🔄 清空对话历史"):
        st.session_state.history = [{"role": "system", "content": system_content}]
        st.rerun()

# ==========================================
# 4. 渲染网页聊天流（自动生成精美的气泡对话）
# ==========================================
# 遍历记忆，把非 system 的对话渲染在网页上
for msg in st.session_state.history:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# ==========================================
# 5. 核心交互流（接收输入 -> 调用 API -> 渲染网页）
# ==========================================
# 这里的 st.chat_input 替代了你原本黑框里的 input()
# 它天然支持直接粘贴多行、长文本标书，完全没有换行报错的 Bug！
if user_input := st.chat_input("请在此处粘贴或输入企业的模拟招标书需求..."):
    
    # 1. 立即在网页上显示用户的输入
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # 将输入追加进历史记忆
    st.session_state.history.append({"role": "user", "content": user_input})

    # 2. 在网页上展示一个高逼格的“正在思考”加载动画
    with st.chat_message("assistant"):
        with st.spinner("⏳ 智能体正在解析标书、检索知识库并动态计算 RFP 矩阵..."):
            
            # 这里就是你原本的 requests.post 调用逻辑
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "deepseek-chat",
                "messages": st.session_state.history,
                "stream": False
            }
            
            try:
                response = requests.post(api_url, headers=headers, json=data)
                response.raise_for_status()
                
                # 提取 AI 的回复内容
                ai_reply = response.json()['choices'][0]['message']['content']
                
                # 直接将结果渲染在网页上（Markdown 表格会自动变成极其精美的可视化表格）
                st.markdown(ai_reply)
                
                # 将 AI 的回复追加进历史记忆
                st.session_state.history.append({"role": "assistant", "content": ai_reply})
                
            except Exception as e:
                st.error(f"❌ 运行出错：{e}，请检查 API Key 或网络状况。")