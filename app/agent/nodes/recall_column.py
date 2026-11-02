import asyncio

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime


from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.models.qdrant.column_info_qdrant import ColumnInfoQdrant
from app.prompt.prompt_loader import load_prompt


async def recall_column(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    await asyncio.sleep(1)
    # 获取流对象
    writer = runtime.stream_writer
    # 输出进度信息
    writer({"stage": "召回字段"})

    try:
        # 获取向量转换对象
        embedding_client=runtime.context["embedding_client"]
        # 获取字段向量召回repository
        column_qdrant_repository= runtime.context["column_qdrant_repository"]
        # 获取用户问题
        query = state["query"]
        # 获取提取的关键字
        keywords = state["keywords"]

        # 1.扩展关键字
        # 1.1 定义提示词模版
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_column_recall"),input_variables=["query"])
        # 1.2 构建输出解析器
        output_parser= JsonOutputParser()
        # 1.3 构建langchain链
        chain = prompt | llm | output_parser
        # 1.4 执行链获取结果
        result=await chain.ainvoke({"query":query})

        # 1.5 合并关键字
        keywords =set(keywords+result)

        # 定义字典去重字段对象
        recall_columns_map:dict[str,ColumnInfoQdrant]={}

        # 2.召回字段
        for keyword in keywords:
            # 2.1 转换向量
            embeddings=await embedding_client.aembed_query(keyword)
            # 2.2 根据向量查询qdrant
            payloads:list[ColumnInfoQdrant]=await column_qdrant_repository.search(embeddings)
            # 2.3 收集返回结果去重处理
            for payload in payloads:
                # 获取id
                column_id=payload["id"]
                # 判断
                if column_id not  in recall_columns_map:
                    recall_columns_map[column_id]= payload

        # 获取去重的字段列表
        recall_columns:list[ColumnInfoQdrant]= list(recall_columns_map.values())


        """
         字段信息示例(recall_columns)：{
            "id": "dim_region.province",
            "name": "province",
            "type": "varchar(64)",
            "role": "dimension",
            "examples": ["广东", "江苏"],
            "description": "省份名称",
            "alias": ["省份", "省"],
            "table_id": "dim_region"
        }

        | 字段 | 作用 |
        |---|---|
        | `id` | 唯一标识字段，也用于和 ES 的值关联 |
        | `name` | 生成 SQL 时使用的真实字段名：`province` |
        | `type` | 判断字段类型，字符串需要加引号，数值通常不需要 |
        | `role` | 判断是维度、度量、主键还是外键 |
        | `examples` | 帮助理解字段真实取值，例如 `广东` 是省份值 |
        | `description` | 解释字段业务含义，避免字段名不直观 |
        | `alias` | 把用户说法映射到字段，例如“省份”对应 `province` |
        | `table_id` | 知道字段属于哪张表：`dim_region` |

        name + table_id
            决定 SQL 中使用哪个表的哪个字段

        description + alias
            帮助理解用户说法对应哪个字段

        examples
            帮助判断“广东”是字段值，而不是字段名

        type
            帮助生成正确条件，例如：
            province = '广东'
            order_amount > 1000

        id
            让 ES 返回的“广东”能关联到 dim_region.province
        """



        logger.info(f"召回字段信息成功：f{list(recall_columns_map.keys())}")

        return {"recall_columns":recall_columns}
    except Exception as e:
        logger.error(f"召回字段信息异常：{str(e)}")
        raise


