import tkinter as tk
from tkinter import simpledialog, messagebox

class InteractiveNodeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Interactive Node Canvas")
        
        # Instructions layout
        instructions = (
            "• Left-Click on empty space: Create a node\n"
            "• Left-Click & Drag a node: Move it around\n"
            "• Right-Click on a node: Delete it\n"
            "• Shift + Left-Click node A, then node B: Connect them"
        )
        self.label = tk.Label(root, text=instructions, justify=tk.LEFT, font=("Arial", 10), bg="#f0f0f0", padx=10, pady=5)
        self.label.pack(fill=tk.X)
        
        # Canvas workspace
        self.canvas = tk.Canvas(root, width=800, height=500, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Event bindings
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<Button-3>", self.on_right_click)  # Windows/Linux Right-Click
        self.canvas.bind("<Button-2>", self.on_right_click)  # macOS Right-Click
        
        # State tracking vars
        self.nodes = {}          # Maps group_tag -> { 'circle': id, 'text': id, 'name': str }
        self.connections = []    # List of tuples: (tag1, tag2, line_id)
        self.selected_node = None
        self.start_connection_node = None
        self.node_counter = 0

    def on_left_click(self, event):
        clicked_item = self.canvas.find_withtag(tk.CURRENT)
        
        # CASE 1: Clicked on an existing node
        if clicked_item:
            # FIXED: Changed get_tags to gettags
            tags = self.canvas.gettags(clicked_item)
            node_tag = [t for t in tags if t.startswith("node_")]
            if not node_tag:
                return
            node_tag = node_tag[0]
            
            # Sub-case: Connecting nodes (Shift + Click)
            if event.state & 0x0001:  
                if not self.start_connection_node:
                    self.start_connection_node = node_tag
                    self.canvas.itemconfig(self.nodes[node_tag]['circle'], fill="#e74c3c") # Highlight red
                else:
                    if self.start_connection_node != node_tag:
                        self.create_connection(self.start_connection_node, node_tag)
                    # Reset highlight
                    self.canvas.itemconfig(self.nodes[self.start_connection_node]['circle'], fill="#3498db")
                    self.start_connection_node = None
            else:
                # Sub-case: Standard click to prepare for dragging
                self.selected_node = node_tag
                self.drag_start_x = event.x
                self.drag_start_y = event.y
                
        # CASE 2: Clicked on empty space -> Create a new node
        else:
            self.start_connection_node = None  # Reset connection state if clicking away
            node_name = simpledialog.askstring("Node Name", "Enter a name for this node:")
            if node_name:
                self.create_node(event.x, event.y, node_name)

    def create_node(self, x, y, name):
        radius = 20
        self.node_counter += 1
        node_tag = f"node_{self.node_counter}"
        
        # Create shapes under a unified tag group
        circle_id = self.canvas.create_oval(
            x - radius, y - radius, x + radius, y + radius, 
            fill="#3498db", outline="#2980b9", width=2, tags=(node_tag, "node_element")
        )
        text_id = self.canvas.create_text(
            x, y + radius + 12, text=name, 
            font=("Arial", 10, "bold"), fill="black", tags=(node_tag, "node_element")
        )
        
        self.nodes[node_tag] = {'circle': circle_id, 'text': text_id, 'name': name}

    def on_drag(self, event):
        if not self.selected_node:
            return
            
        # Calculate cursor movement delta
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        # Move both circle and text together
        self.canvas.move(self.selected_node, dx, dy)
        
        # Update coordinate memory for continuous dragging
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
        # Redraw lines connected to this shifted node
        self.update_connections()

    def create_connection(self, tag1, tag2):
        # Prevent duplicate lines
        for t1, t2, _ in self.connections:
            if (t1 == tag1 and t2 == tag2) or (t1 == tag2 and t2 == tag1):
                return
                
        # Get coordinates of both nodes
        x1, y1 = self.get_node_center(tag1)
        x2, y2 = self.get_node_center(tag2)
        
        # Render line behind nodes
        line_id = self.canvas.create_line(x1, y1, x2, y2, width=2, fill="#7f8c8d")
        self.canvas.tag_lower(line_id) 
        
        self.connections.append((tag1, tag2, line_id))

    def update_connections(self):
        for i, (tag1, tag2, line_id) in enumerate(self.connections):
            x1, y1 = self.get_node_center(tag1)
            x2, y2 = self.get_node_center(tag2)
            self.canvas.coords(line_id, x1, y1, x2, y2)

    def on_right_click(self, event):
        clicked_item = self.canvas.find_withtag(tk.CURRENT)
        if not clicked_item:
            return
            
        # FIXED: Changed get_tags to gettags
        tags = self.canvas.gettags(clicked_item)
        node_tag = [t for t in tags if t.startswith("node_")]
        if not node_tag:
            return
        node_tag = node_tag[0]
        
        # Confirm deletion
        confirm = messagebox.askyesno("Delete Node", f"Are you sure you want to delete node '{self.nodes[node_tag]['name']}'?")
        if confirm:
            # 1. Clear associated visual elements
            self.canvas.delete(node_tag)
            
            # 2. Drop active lines tied to this node
            remaining_connections = []
            for t1, t2, line_id in self.connections:
                if t1 == node_tag or t2 == node_tag:
                    self.canvas.delete(line_id)
                else:
                    remaining_connections.append((t1, t2, line_id))
            self.connections = remaining_connections
            
            # 3. Purge memory track
            del self.nodes[node_tag]
            
            if self.selected_node == node_tag:
                self.selected_node = None

    def get_node_center(self, node_tag):
        # Calculate midpoints using visual bounding box dimensions
        x1, y1, x2, y2 = self.canvas.coords(self.nodes[node_tag]['circle'])
        return (x1 + x2) / 2, (y1 + y2) / 2

if __name__ == "__main__":
    root = tk.Tk()
    app = InteractiveNodeApp(root)
    root.mainloop()
