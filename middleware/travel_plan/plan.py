from langchain_qwq import ChatQwen
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain.agents.middleware import ToolRetryMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.structured_output import ToolStrategy
import asyncio
import time
from schema import Plan
import json



load_dotenv()

async def plan(city, days):
    city = city
    days = days
    model = ChatQwen(model="qwen3-max")
   
    client = MultiServerMCPClient(
        {
            "MapMcp":{
                "transport": "streamable_http",
                "url": "https://mcp.amap.com/mcp?key=a01d4ae739e4953f919cd5b27afcdacd"
            },
            "WebSearch": {
                "transport": "streamable_http",
                "url": "https://open.bigmodel.cn/api/mcp-broker/proxy/web-search/mcp",
                "headers": {
                    "Authorization": "2c28d5ae747b4a7fba1bb9ce9ac5f09c.OpF7pbGrExrVnbTm"
                }
            }
            
        }
    )
    tools = await client.get_tools()

    agent = create_agent(
        model= model,
        system_prompt="你是一名资深的智能旅行规划专家。",
        tools= tools,
        middleware=[ToolRetryMiddleware(
            max_retries=3,  # Retry up to 3 times
            on_failure="raise",
        ),
        ],
        response_format= ToolStrategy(schema=Plan)
    )
    content = f"""你需要规划一份{city}的{days}天旅游规划。请严格按照以下步骤进行思考和执行：
1.  **信息检索 (Search)**:
    * 检索目的地的热门景点、特色美食、高评分餐厅和推荐酒店。对热门景点和特色美食使用webSearchStd检索，对餐厅和酒店使用高德地图MCP检索。
    * 获取每个地点的具体地址、营业时间、门票价格、游玩建议时长。游玩时长使用webSearchStd检索，其余信息优先使用高德地图MCP进行检索。
    * 查询景点之间的地理位置关系，以规划合理的路线。

2.  **路线规划 (Planning Logic)**:
    * **地理聚类**: 将距离较近的景点安排在同一天，避免往返跑路。
    * **逻辑连贯**: 在时间轴 (`timeline`) 中，必须严格遵循“景点 A -> 交通 -> 景点 B”的逻辑。除了每天的第一个景点外，每个景点之前都应该有一个 `Transportation` 节点，说明如何从上一处到达此处。
    * **时间管理**: 确保游玩时长和交通时长加起来符合一天的正常活动范围(大致在9:00-18:00)，不要过早结束一天的行程。一天安排3个景点，不要出现重复。安排行程需要考虑留出就餐时间(但不要把吃饭写到规划中！)。晚上如果安排景点需要确保景点是开放的。

# Constraints & Rules
* **Timeline 结构**: `timeline` 列表必须混合包含 `SpotVisit` 和 `Transportation` 对象，按时间顺序排列。
    * 错误示例: [Spot A, Spot B, Spot C]
    * 正确示例: [Spot A, Transport(to B), Spot B, Transport(to C), Spot C]
* **真实性**: 地址 (`address`) 、价格(`cost`) 、评分(`rating`) 必须真实存在，不要编造。
* **推荐列表**:`Food`, `Restaurants` 和 `Hotels` 列表是作为全局推荐提供的，不需要插入到每天的 `timeline` 中。且每个要包括五个推荐。
* **工具使用**: 使用fetch_webpage时可以多抓取几个不同id的网页，防止有些网站有反爬虫措施导致无法获取内容。
"""
    # content = "搜索一下游玩苏州博物馆需要多少时间"
    respond = await agent.ainvoke(
        {"messages":[{"role": "user", "content":content }]}
    )
    
    print("\n***********Structured Response***********\n")
    plan: Plan = respond["structured_response"]
    with open(f"{city}_{days}days_plan.json", "w", encoding="utf-8") as f:
        json.dump(plan.model_dump(), f, ensure_ascii=False, indent=2)
    print(plan.model_dump_json(indent=2, ensure_ascii=False))

    print("\n***********Raw Response***********\n")
    with open(f"content.json", "w", encoding="utf-8") as f:
        for msg in respond["messages"]:
            print(msg)
            f.write(repr(msg)+"\n")
            print("\n")
    
    return f"{city}_{days}days_plan.json"

if __name__ == "__main__":
    path = asyncio.run(plan(city="苏州", days=3))

