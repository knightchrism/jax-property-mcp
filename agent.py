import asyncio, json, sys
import ollama
from mcp import ClientSession, StdioServerParameters, stdio_client

MODEL = "qwen3:30b"
SERVER = StdioServerParameters(command=sys.executable, args=["server.py"])


async def main(question: str):
    # 1. Start server.py and connect to it over stdin/stdout
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 2. Ask the server for its tools and convert them to Ollama's format
            listed = await session.list_tools()
            tools = [{"type": "function", "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": getattr(t, "input_schema", None) or getattr(t, "inputSchema", {})}}
                     for t in listed.tools]
            print("Tools:", [t["function"]["name"] for t in tools])

            messages = [
                {"role": "system", "content": "You answer questions about Jacksonville real estate. Use the tools; never make up properties."},
                {"role": "user", "content": question},
            ]

            # 3. The agent loop: ask the model, run any tools it picks, repeat
            for step in range(6):
                reply = ollama.chat(model=MODEL, messages=messages, tools=tools, think=False)
                msg = reply.message
                messages.append(msg)
                if not msg.tool_calls:
                    print("\nAnswer:\n" + msg.content.split("</think>")[-1].strip())
                    return
                for call in msg.tool_calls:
                    name, args = call.function.name, dict(call.function.arguments)
                    print(f"-> calling {name}({args})")
                    result = await session.call_tool(name, args)
                    text = "\n".join(getattr(c, "text", "") for c in result.content)
                    messages.append({"role": "tool", "tool_name": name, "content": text})
            print("Stopped after 6 steps.")


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "Find 3 homes in ZIP 32207 worth between 200000 and 400000."
    asyncio.run(main(q))

