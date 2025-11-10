from typing import Optional

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

# This file is deprecated - TruthWeb functionality is now in app.py
# Keeping for reference but not used
from .questions import QUESTION_SETS


class TruthWebWindow:
    def __init__(self, app: "SurveyApp", controller: "SurveyController"):
        self.app = app
        self.controller = controller
        
        # Create window and store reference in app to keep it alive
        self.window = toga.Window(title="TruthWeb", size=(800, 600))
        # Store window reference in app to prevent garbage collection
        if not hasattr(app, '_truth_web_windows'):
            app._truth_web_windows = []
        app._truth_web_windows.append(self.window)
        
        # Create scrollable container
        scroll = toga.ScrollContainer(style=Pack(flex=1))
        
        # Main container
        box = toga.Box(style=Pack(direction=COLUMN, padding=16))
        
        title = toga.Label("TruthWeb Visualization", style=Pack(padding=(0, 0, 8, 0)))
        legend = toga.Label(
            "🔴 Red lines = Contradictions | 🟢 Green lines = Requirements\n"
            "🔵 Blue = Agreed | ⚪ Gray = Disagreed | ⚪ Light gray = Unanswered",
            style=Pack(padding=(0, 0, 16, 0))
        )
        box.add(title)
        box.add(legend)
        
        # Create visualization using labels and lines (approximated)
        viz_box = self._create_visualization()
        box.add(viz_box)
        
        scroll.content = box
        self.window.content = scroll
        
    def show(self):
        self.window.show()
    
    def _create_visualization(self) -> toga.Box:
        """Create a widget-based visualization"""
        container = toga.Box(style=Pack(direction=COLUMN, padding=8))
        
        # Get relationships
        contradictions = self.controller.detect_contradictions()
        requirements = self.controller.detect_requirements()
        
        # Show all questions as nodes
        container.add(toga.Label("Questions:", style=Pack(padding=(8, 0, 4, 0))))
        
        # Use controller's question set instead of global QUESTIONS
        question_set = self.controller.question_set
        for i in range(len(question_set)):
            key = self.controller._key_for(i)
            answered = key in self.controller.answers
            agreed = False
            if answered:
                agreed = self.controller.answers[key][1]
            
            # Determine status emoji and color indicator
            if not answered:
                status = "⚪"
                status_text = "Unanswered"
            elif agreed:
                status = "🔵"
                status_text = "Agreed"
            else:
                status = "⚪"
                status_text = "Disagreed"
            
            # Create node representation
            node_box = toga.Box(style=Pack(direction=ROW, padding=4))
            node_label = toga.Label(
                f"{status} Q{i+1}: {question_set[i]['text']} ({status_text})",
                style=Pack(padding=4, flex=1)
            )
            node_box.add(node_label)
            container.add(node_box)
        
        # Show contradictions
        if contradictions:
            container.add(toga.Label(
                "🔴 Contradictions (Red):",
                style=Pack(padding=(16, 0, 4, 0))
            ))
            for i, j, q1, q2 in contradictions:
                contr_label = toga.Label(
                    f"  Q{i+1} ↔ Q{j+1}",
                    style=Pack(padding=4)
                )
                container.add(contr_label)
        
        # Show requirements
        if requirements:
            container.add(toga.Label(
                "🟢 Requirements (Green):",
                style=Pack(padding=(16, 0, 4, 0))
            ))
            for i, j, q1, q2 in requirements:
                req_label = toga.Label(
                    f"  Q{i+1} → Q{j+1}",
                    style=Pack(padding=4)
                )
                container.add(req_label)
        
        if not contradictions and not requirements:
            container.add(toga.Label(
                "No relationships detected",
                style=Pack(padding=(16, 0, 4, 0))
            ))
        
        return container

