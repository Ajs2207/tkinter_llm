import os
import json
import random
import threading
import tkinter as tk
from tkinter import messagebox
from dotenv import load_dotenv
from fireworks.client import Fireworks  # Use official Fireworks library

# Load environment variables from a .env file
load_dotenv()

# Fetch API key
api_key = os.environ.get("FIREWORKS_API_KEY")
if not api_key:
    raise ValueError("Error: FIREWORKS_API_KEY environment variable not found.")

# Initialize the official Fireworks client
client = Fireworks(api_key=api_key)

# The requested target model
MODEL_NAME = "accounts/fireworks/models/minimax-m2p7"

class FireworksNodeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Fireworks AI-Controlled Node Canvas")
        
        # --- UI LAYOUT ---
        # Top Info Bar
        instructions = "Type instructions below (e.g., 'Create node Alpha', 'Connect Alpha to Beta', 'Delete Alpha')"
        self.label = tk.Label(root, text=instructions, font=("Arial", 10, "italic"), bg="#f0f0f0", pady=5)
        self.label.pack(fill=tk.X)
        
        # Canvas Workspace
        self.canvas = tk.Canvas(root, width=800, height=450, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Bottom Control Panel
        self.control_frame = tk.Frame(root, pady=10, bg="#e0e0e0")
        self.control_frame.pack(fill=tk.X)
        
        self.entry_label = tk.Label(self.control_frame, text="Command:", font=("Arial", 11, "bold"), bg="#e0e0e0")
        self.entry_label.pack(side=tk.LEFT, padx=10)
        
        self.command_entry = tk.Entry(self.control_frame, font=("Arial", 12))
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.command_entry.bind("<Return>", lambda event: self.process_llm_command())
        
        self.send_btn = tk.Button(self.control_frame, text="Execute", command=self.process_llm_command, bg="#2ecc71", fg="white", font=("Arial", 10, "bold"))
        self.send_btn.pack(side=tk.RIGHT, padx=10)
        
        # --- STATE MANAGEMENT ---
        self.nodes = {}          # Maps user_given_name (lowercase) -> { 'circle': id, 'text': id, 'name': original_case_str }
        self.connections = []    # List of tuples: (name1, name2, line_id)
        
    # --- AUTOMATIC COORDINATE ALLOCATION ---
    def get_smart_coordinates(self):
        """Finds a random, non-overlapping location on the canvas for a new node."""
        radius = 20
        for _ in range(100):
            x = random.randint(50, 750)
            y = random.randint(50, 400)
            
            overlapping = False
            for node_info in self.nodes.values():
                nx1, ny1, nx2, ny2 = self.canvas.coords(node_info['circle'])
                cx, cy = (nx1 + nx2) / 2, (ny1 + ny2) / 2
                distance = ((x - cx)**2 + (y - cy)**2)**0.5
                if distance < 60:
                    overlapping = True
                    break
            if not overlapping:
                return x, y
        return random.randint(100, 700), random.randint(100, 350)

    # --- CORE CANVAS ACTION API ---
    def ui_create_node(self, name):
        name_lower = name.lower().strip()
        if name_lower in self.nodes:
            return f"Node '{name}' already exists."
        
        x, y = self.get_smart_coordinates()
        radius = 20
        
        circle_id = self.canvas.create_oval(
            x - radius, y - radius, x + radius, y + radius, 
            fill="#3498db", outline="#2980b9", width=2, tags=name_lower
        )
        text_id = self.canvas.create_text(
            x, y + radius + 12, text=name, 
            font=("Arial", 10, "bold"), fill="black", tags=name_lower
        )
        
        self.nodes[name_lower] = {'circle': circle_id, 'text': text_id, 'name': name}
        return f"Successfully created node '{name}'."

    def ui_connect_nodes(self, node_a, node_b):
        a_lower = node_a.lower().strip()
        b_lower = node_b.lower().strip()
        
        if a_lower not in self.nodes or b_lower not in self.nodes:
            return f"Error: One or both nodes ('{node_a}', '{node_b}') do not exist."
        if a_lower == b_lower:
            return "Cannot connect a node to itself."
            
        for t1, t2, _ in self.connections:
            if (t1 == a_lower and t2 == b_lower) or (t1 == b_lower and t2 == a_lower):
                return f"Nodes '{node_a}' and '{node_b}' are already connected."
                
        ax1, ay1, ax2, ay2 = self.canvas.coords(self.nodes[a_lower]['circle'])
        bx1, by1, bx2, by2 = self.canvas.coords(self.nodes[b_lower]['circle'])
        
        line_id = self.canvas.create_line(
            (ax1+ax2)/2, (ay1+ay2)/2, (bx1+bx2)/2, (by1+by2)/2, 
            width=2, fill="#7f8c8d"
        )
        self.canvas.tag_lower(line_id) 
        
        self.connections.append((a_lower, b_lower, line_id))
        return f"Successfully connected '{node_a}' to '{node_b}'."

    def ui_delete_node(self, name):
        name_lower = name.lower().strip()
        if name_lower not in self.nodes:
            return f"Node '{name}' does not exist."
            
        self.canvas.delete(name_lower)
        
        remaining_connections = []
        for t1, t2, line_id in self.connections:
            if t1 == name_lower or t2 == name_lower:
                self.canvas.delete(line_id)
            else:
                remaining_connections.append((t1, t2, line_id))
        self.connections = remaining_connections
        
        del self.nodes[name_lower]
        return f"Successfully deleted node '{name}'."

    # --- LLM API INTEGRATION LAYER ---
    def process_llm_command(self):
        user_prompt = self.command_entry.get().strip()
        if not user_prompt:
            return
            
        self.command_entry.delete(0, tk.END)
        self.send_btn.config(state=tk.DISABLED, text="Thinking...")
        
        threading.Thread(target=self.call_fireworks_api, args=(user_prompt,), daemon=True).start()

    def show_status(self, text):
        self.label.config(text=text, fg="#2c3e50")
        

    def get_current_board_state(self):
        """Generates a text summary of all active nodes and connections for the LLM context."""
        if not self.nodes:
            return "The board is currently completely empty. No nodes exist yet."
            
        active_nodes = [info['name'] for info in self.nodes.values()]
        state_str = f"Current existing nodes on the board: {', '.join(active_nodes)}.\n"
        
        if self.connections:
            links = []
            for t1, t2, _ in self.connections:
                # Retrieve original case names from memory mapping
                name1 = self.nodes[t1]['name']
                name2 = self.nodes[t2]['name']
                links.append(f"{name1}—{name2}")
            state_str += f"Current active connections: {', '.join(links)}."
        else:
            state_str += "There are no connections drawn between any nodes yet."
            
        return state_str

    def call_fireworks_api(self, prompt):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "ui_create_node",
                    "description": "Creates a new structural circle node on the visual canvas workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "The custom display name of the node."}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "ui_connect_nodes",
                    "description": "Draws a link/line connecting two pre-existing nodes together.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "node_a": {"type": "string", "description": "The name of the origin node."},
                            "node_b": {"type": "string", "description": "The name of the target destination node."}
                        },
                        "required": ["node_a", "node_b"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "ui_delete_node",
                    "description": "Removes a specific node and its associated links from the board completely.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "The exact name of the node to remove."}
                        },
                        "required": ["name"]
                    }
                }
            }
        ]
        try:
            # Fetch the live layout snapshot right before sending to the model
            board_context = self.get_current_board_state()

            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "You are a specialized layout assistant mapping user speech patterns to exact interface toolkit modifications.\n"
                            f"IMPORTANT STATE CONTEXT:\n{board_context}"
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                tools=tools,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=150
            )
            # Explicitly target index 0 of the choices list
            if not response.choices:
                self.root.after(0, lambda: self.show_status("Empty response from AI model."))
                return
            
            response_message = response.choices[0].message
            tool_calls = getattr(response_message, 'tool_calls', None)
            
            if tool_calls:
                for tool_call in tool_calls:
                    func_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments) 
                    
                    if func_name == "ui_create_node":
                        self.root.after(0, lambda name=args.get("name"): self.show_status(self.ui_create_node(name)))
                    elif func_name == "ui_connect_nodes":
                        self.root.after(0, lambda a=args.get("node_a"), b=args.get("node_b"): self.show_status(self.ui_connect_nodes(a, b)))
                    elif func_name == "ui_delete_node":
                        self.root.after(0, lambda name=args.get("name"): self.show_status(self.ui_delete_node(name)))
            else:
                msg = response_message.content or "No actionable command understood."
                self.root.after(0, lambda m=msg: messagebox.showinfo("Fireworks Response", m))
                
        except Exception as api_error:
            error_msg = f"Failed calling Fireworks AI:\n{str(api_error)}"
            self.root.after(0, lambda em=error_msg: messagebox.showerror("API Error", em))
            
        finally:
            self.root.after(0, lambda: self.send_btn.config(state=tk.NORMAL, text="Execute"))

if __name__ == "__main__":
    root = tk.Tk()
    app = FireworksNodeApp(root)
    root.mainloop()
