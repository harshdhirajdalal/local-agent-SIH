import asyncio
import json
import websockets


SESSION_ID = "functiongemma-e2e-test"


async def main():
    uri = f"ws://localhost:8000/ws/browser/{SESSION_ID}"

    async with websockets.connect(uri) as ws:
        print("CONNECTED")

        # Send browser state
        browser_state = {
            "type": "browser_state",
            "session_id": SESSION_ID,

            "page": {
                "url": "https://example.com/search",
                "title": "Example Search"
            },

            "viewport": {
                "width": 1904,
                "height": 948,
                "dpr": 1,
                "scrollX": 0,
                "scrollY": 0
            },

            "dom": {
                "elements": [
                    {
                        "id": "search-box",
                        "type": "textbox",
                        "label": "Search",
                        "placeholder": "Search here",
                        "visible": True,
                        "interactive": True,
                        "sensitive": False,
                        "bbox": {
                            "x": 100,
                            "y": 200,
                            "width": 400,
                            "height": 40
                        }
                    },
                    {
                        "id": "search-button",
                        "type": "button",
                        "label": "Search",
                        "text": "Search",
                        "visible": True,
                        "interactive": True,
                        "sensitive": False,
                        "bbox": {
                            "x": 510,
                            "y": 200,
                            "width": 100,
                            "height": 40
                        }
                    }
                ]
            },

            "visual": {
                "elements": []
            }
        }

        print("\nSending browser state...")
        await ws.send(json.dumps(browser_state))

        # Give the server a moment to process state
        await asyncio.sleep(0.2)

        # Send task
        task = {
            "type": "task",
            "session_id": SESSION_ID,
            "step_id": "e2e-functiongemma-1",
            "user_request": "Search for ASUS TUF A16"
        }

        print("Sending task...")
        await ws.send(json.dumps(task))

        print("\nWaiting for server...\n")

        while True:
            message = await ws.recv()

            print("SERVER:")
            print(json.dumps(json.loads(message), indent=2))

            data = json.loads(message)

            if data.get("type") in {
                "agent_result",
                "error"
            }:
                break


if __name__ == "__main__":
    asyncio.run(main())
