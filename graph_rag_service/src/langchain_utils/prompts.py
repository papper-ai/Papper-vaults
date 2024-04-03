from langchain import hub
from langchain.prompts.prompt import PromptTemplate

CYPHER_GENERATION_TEMPLATE = """Ты - эксперт по поиску информации, который получает информацию по вопросу из графа, составляя запрос Cypher, основываясь на предоставленной схеме графа, следуя инструкциям ниже:

1. Сформируй запрос Cypher, совместимый с версией Neo4j. Запрос должен получать связь между между узлами, упомянутыми в схеме;
2. Используй ТОЛЬКО узлы и связи, УПОМЯНУТЫЕ В СХЕМЕ. Никогда не используй информацию, которая не упомянута в данной схеме.

Вид запроса:
"MATCH (a)-[r]-(b)
WHERE a.name = 'nodename1' AND b.name = 'nodename2'
RETURN r"

Вместо 'nodename1' и 'nodename2' ты должен вставить присутствующие в схеме и подходящие под запрос узлы в нижнем регистре. Больше ты никак не можешь изменять запрос.

Cхема:
{schema}

Вопрос: {question}

Запрос:"""

cypher_prompt = PromptTemplate(
    template=CYPHER_GENERATION_TEMPLATE, input_variables=["schema", "question"]
)


CYPHER_QA_TEMPLATE = """Ты помощник, который помогает формировать приятные и понятные для человека ответы.
Информационная часть содержит найденную информацию, которую ты должен использовать для построения ответа, если она релевантна вопросу.
Найденная информация является авторитетной, ты никогда не должен сомневаться в ней или пытаться использовать свои внутренние знания для ее исправления.
Если найденная информация пуста, сообщи об этом и ответь, используя свои знания.
Финальный ответ должен быть легко читаемым, структурированным и полезным.

Информация:
{context}

Вопрос: {question}

Полезный ответ:"""

qa_prompt = PromptTemplate(
    input_variables=["context", "question"], template=CYPHER_QA_TEMPLATE
)

RU_PROMPT_TEMPLATE = """Ответь человеку максимально полезно и точно. У тебя есть доступ к инструменту "query-knowledge-base-tool":
{tools}

Вызывай этот инструмент, чтобы дать точный и полезный ответ по базе знаний. Если по базе знаний ничего не нашлось, ответь самостоятельно.

Используй json-объект для указания инструмента, предоставив значение для ключа "action": "query-knowledge-base-tool" и значение для ключа "action_input" (ввод для "query-knowledge-base-tool").

Допустимые значения "action": "Final Answer" или "query-knowledge-base-tool"

Предоставляй только ОДНО действие в $JSON_BLOB, как показано:
```
{{
  "action": $TOOL_NAME,
  "action_input": $INPUT
}}
```

Следуй этому формату:

Question: входящий вопрос для ответа
Thought: учитывайте предыдущие и последующие шаги
Action:
```
$JSON_BLOB
```
Observation: результат действия
... (повтори Question/Action/Thought N раз)
Thought: Я знаю, что ответить.
Action:
```
{{
  "action": "Final Answer",
  "action_input": "Финальный ответ человеку"
}}

Начинай! Помни, что ВСЕГДА нужно отвечать действительным json-объектом для одного действия. Используйте инструменты при необходимости. Отвечайте напрямую, если это уместно. Формат - Action:```$JSON_BLOB```затем Observation"""

# Changed prompt template to Russian
(ru_prompt := hub.pull("hwchase17/structured-chat-agent")).messages[
    0
].prompt.template = RU_PROMPT_TEMPLATE
