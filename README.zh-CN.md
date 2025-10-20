# 高级后端工程师（AI方向）- 编程评测

你好！

感谢你参与本次招聘流程。本次评测旨在考察你在AI应用开发领域的综合能力，特别是利用大型语言模型（LLM）解决实际问题的工程、设计和创造能力。请仔细阅读以下说明。

---

## 场景描述

你的任务是构建一个AI Agent。这个Agent能够接收代码和需求，然后对代码进行分析，并输出一份结构化的分析报告。Agent可以使用NodeJs/Python/N8N开发。

## Agent的输入

你的Agent需要设计成一个接受 `multipart/form-data` 请求的API服务。该服务接收以下两个部分：

1.  **`problem_description`** (string, form field): 一段描述项目应实现功能的自然语言文字。
2.  **`code_zip`** (file, form upload): 一个包含项目完整源代码的zip压缩文件。

## 核心任务 (必须完成)

**目标：生成一份代码功能定位报告。**

Agent需要分析代码，并输出一份JSON报告。这份报告需要清晰地指出，为了实现`problem_description`中描述的各项功能，代码仓库中的哪些部分是关键的实现点。

**JSON报告结构示例：**

```json
{
  "feature_analysis": [
    {
      "feature_description": "实现`创建频道`功能",
      "implementation_location": [
        {
          "file": "src/modules/channel/channel.resolver.ts",
          "function": "createChannel",
          "lines": "13-16"
        },
        {
          "file": "src/modules/channel/channel.service.ts",
          "function": "create",
          "lines": "21-24"
        }
      ]
    },
    {
      "feature_description": "实现`在频道中发送消息`功能",
      "implementation_location": [
        {
          "file": "src/modules/message/message.resolver.ts",
          "function": "createMessage",
          "lines": "13-16"
        },
        {
          "file": "src/modules/message/message.service.ts",
          "function": "create",
          "lines": "23-34"
        }
      ]
    },
    {
      "feature_description": "实现`按时间倒序列出频道中的消息`功能",
      "implementation_location": [
        {
          "file": "src/modules/message/message.resolver.ts",
          "function": "findAll",
          "lines": "18-21"
        },
        {
          "file": "src/modules/message/message.service.ts",
          "function": "findAll",
          "lines": "41-66"
        }
      ]
    }
  ],
  "execution_plan_suggestion": "要执行此项目，应首先执行 `npm install` 安装依赖，然后执行 `npm run start:dev` 来启动服务。该服务是一个GraphQL API，可以在 http://localhost:3000/graphql 访问。"
}
```

## 加分项 (可选)

**目标：动态验证功能的正确性。**

在完成核心任务的基础上，如果你能让Agent更进一步，**自动验证**是否能正确工作，并给出**可执行的单元测试**，你将获得极大的加分。

这通常意味着你的Agent需要具备动态生成和执行测试代码的能力。

**包含加分项的JSON报告结构示例：**

```json
{
  "feature_analysis": {
    "...": "..."
  },
  "functional_verification": {
    "generated_test_code": "const request = require('supertest');\nconst assert = require('assert');\n\ndescribe('GraphQL API', () => {\n  it('should create a channel and then a message in it', async () => {\n    const server = 'http://localhost:3000';\n    const createChannelQuery = `mutation { createChannel(createChannelInput: { name: \"New Channel\" }) { id, name } }`;\n    const channelRes = await request(server).post('/graphql').send({ query: createChannelQuery });\n    const channelId = channelRes.body.data.createChannel.id;\n\n    const createMessageQuery = `mutation { createMessage(createMessageInput: { channelId: ${channelId}, title: \"Hello\", content: \"World\" }) { id, title } }`;\n    const messageRes = await request(server).post('/graphql').send({ query: createMessageQuery });\n\n    assert.equal(messageRes.body.data.createMessage.title, 'Hello');\n  });\n});",
    "execution_result": {
      "tests_passed": true,
      "log": "1 passing (2s)"
    }
  }
}
```

## 交付要求

1.  **Agent源代码**: 提供你的Agent的完整源代码的GitHub仓库地址。请确保代码结构清晰，并包含必要的说明文件。
2.  **可执行环境**: 提供一种标准化的方式来执行你的Agent。请在以下两种方式中**任选其一**：
    *   **选项A (推荐):** 在源代码仓库中包含一个 `Dockerfile` 及相关说明，使我们能够通过 `docker build` 和 `docker run` 快速启动你的Agent服务。
    *   **选项B:** 如果你使用n8n等工作流工具，请提供可直接导入的工作流文件（`.json`格式）及必要的配置说明。

## 评判标准

我们将从以下几个维度综合评估你的成果：

*   **任务完成度**: 是否完整、准确地实现了核心任务的要求。
*   **加分项实现**: 是否挑战并实现了加分项，以及实现的质量。
*   **代码质量**: 你的Agent源代码是否结构清晰、易于理解和维护。
*   **设计思路**: 你在Agent设计中（如Prompt Engineering、工作流设计、错误处理等）体现的思考深度。

## 评测用的示例数据

在开发和测试过程中，可以使用我们提供的示例项目（example1），也可以自行使用github上的项目进行测试。
示例项目中的`example1/examination.md`内容是完整的`problem_description`。