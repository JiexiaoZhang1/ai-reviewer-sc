# AI Agent 编程评测说明

本仓库用于“高级后端工程师（AI 方向）- 编程评测”。

---

## 评测任务回顾

- **输入格式**：`multipart/form-data`
  - `problem_description`：项目需求描述，字符串字段。
  - `code_zip`：完整项目源码的 zip 文件。
- **核心目标**：返回 JSON 报告，列出每个需求点对应的代码位置（文件、函数、行号），并给出执行建议。
- **可选加分**：自动生成/执行测试并回填结果。

示例输出结构：

```json
{
  "feature_analysis": [
    {
      "feature_description": "实现「创建频道」功能",
      "implementation_location": [
        {"file": "src/modules/channel/channel.resolver.ts", "function": "ChannelResolver.createChannel", "lines": "12-34"},
        {"file": "src/modules/channel/channel.service.ts", "function": "ChannelService.create", "lines": "25-61"}
      ]
    }
  ],
  "execution_plan_suggestion": "先执行 npm install 再 npm run start:dev，GraphQL Playground 位于 http://localhost:3000/graphql"
}
```

---

## Agent 功能概览

- **技术栈**：Python 3.11、FastAPI、OpenAI Responses API（GPT-5）。
- **工作流**：
  1. 解压上传的项目，过滤依赖与临时目录。
  2. 依据启发式对源文件排序，并对超大文件按 token 分块。
  3. 用 GPT-5 为每个候选片段生成中文摘要，提取函数/方法名与行号。
  4. 汇总目录树、摘要、符号表，再次调用 GPT-5 生成最终报告。
- **配置**：所有参数集中在 `app/config.py`；在使用前必须将其中的 `OPENAI_API_KEY_PLACEHOLDER` 替换为你自己的 OpenAI API Key，否则服务无法启动。

---

## 使用前准备

1. 打开 `app/config.py`。
2. 将常量 `OPENAI_API_KEY_PLACEHOLDER` 的值替换为真实的 OpenAI API Key（必须具备访问 GPT-5 Responses API 的权限）。请保留 `PLACEHOLDER_SENTINEL` 常量不变。
3. 保存文件后再继续下面的运行步骤。

---

## 快速开始

### 方式一：本地运行

1. （必做）按照“使用前准备”完成 API Key 设置。
2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```
3. 启动服务
   ```bash
   uvicorn app.api:app --host 0.0.0.0 --port 8000
   ```
4. 健康检查  
   访问 `http://127.0.0.1:8000/health`，若返回 `{"status":"ok"}` 表示启动成功。
5. 发送分析请求
   ```bash
   curl -X POST http://127.0.0.1:8000/analyze \
     --form-string "problem_description=$(cat example1/examination.md)" \
     -F code_zip=@example1/nestjs-channel-messenger-demo-main.zip
   ```
   返回即为中文 JSON 报告。

### 方式二：Docker

1. 在构建镜像前，先按照“使用前准备”修改 `app/config.py` 中的 API Key。
2. 构建镜像
   ```bash
   docker build -t ai-reviewer-agent .
   ```
3. 运行容器
   ```bash
   docker run --rm -p 8000:8000 ai-reviewer-agent
   ```
4. 其余操作（健康检查、`curl` 调用）与本地运行一致。

---

## API 说明

- `POST /analyze`  
  - 请求：`multipart/form-data`，字段同“评测任务回顾”。  
  - 响应：结构化 JSON 报告，字段包括 `feature_analysis`、`execution_plan_suggestion`，内容为中文。
- `GET /health`  
  - 返回 `{"status":"ok"}` 用于可用性检查。

---

## 调参与扩展

- 环境变量
  - `MAX_CANDIDATE_FILES`：最多分析的文件数量，默认 `200`。
  - `MAX_FILE_BYTES`：单文件大小上限（字节），默认 `200000`。
  - `MAX_TOKENS_PER_CHUNK`：代码分块的最大 token 数，默认 `1800`。
  - 其余参数见 `app/config.py` 注释。
- 若要加速调试，可降低 `MAX_CANDIDATE_FILES` 或删除 zip 中无关目录。
- 若希望生成或执行测试，可在现有管线后增加自定义步骤（本实现未自动执行加分项）。

---

## 示例数据

`example1` 目录包含：

- `examination.md`：示例 `problem_description`。
- `nestjs-channel-messenger-demo-main.zip`：可供本地调试的 NestJS 项目。

---

## 目录结构

```
app/
  api.py              # FastAPI 入口
  codebase.py         # 文件筛选与符号提取
  config.py           # 配置与环境变量
  report.py           # 报告汇总与 LLM 调用
  storage.py          # zip 解压与目录清理
  summarizer.py       # 代码摘要模块
Dockerfile            # 容器化入口
requirements.txt      # Python 依赖
example1/             # 评测示例数据
```

--- 

## 常见问题

- **为何 `curl` 没响应？** 代码库大时需要多次调用 GPT，处理过程较慢，可调小 `MAX_CANDIDATE_FILES`。
- **提示缺少 API Key？** 请确认已在 `app/config.py` 将 `OPENAI_API_KEY_PLACEHOLDER` 替换为有效 Key，并在修改后重启服务。
- **返回的函数为何没有行号？** 当前版本已强制模型引用符号表填充函数与行号，若为空请检查上传代码是否能解析。
