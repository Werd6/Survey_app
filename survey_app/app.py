import math
from pathlib import Path
from typing import Optional, Tuple, List

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, CENTER, ROW

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from .questions import QUESTION_SETS
from .storage import load_answers, save_answers


class SurveyController:
    def __init__(self, app: "SurveyApp", question_set_name: str) -> None:
        self.app = app
        self.question_set_name = question_set_name
        self.question_set = QUESTION_SETS[question_set_name]
        self.answers = load_answers(self.responses_path)
        self.current_index = self._compute_next_index()

    @property
    def responses_path(self) -> Path:
        # Use set-specific filename
        return self.app.paths.data / f"responses_{self.question_set_name}.json"

    def _compute_next_index(self) -> int:
        for i in range(len(self.question_set)):
            key = self._key_for(i)
            if key not in self.answers:
                return i
        return len(self.question_set)

    def _key_for(self, index: int) -> str:
        return f"q{index + 1}"

    def is_complete(self) -> bool:
        return self.current_index >= len(self.question_set)

    def record_answer(self, value: bool) -> None:
        if self.is_complete():
            return
        key = self._key_for(self.current_index)
        question_data = self.question_set[self.current_index]
        question_text = question_data["text"]
        self.answers[key] = [question_text, value]
        save_answers(self.responses_path, self.answers)
        self.current_index += 1

    def restart(self) -> None:
        self.answers = {}
        save_answers(self.responses_path, self.answers)
        self.current_index = 0

    def detect_contradictions(self) -> list[tuple[int, int, str, str]]:
        """
        Returns list of (q1_index, q2_index, q1_text, q2_text) for contradictory answers.
        Two questions contradict if:
        - They are in each other's contradicts list
        - Both were answered "Agree" (True)
        """
        contradictions = []
        for i in range(len(self.question_set)):
            key_i = self._key_for(i)
            if key_i not in self.answers:
                continue
            
            question_i = self.question_set[i]
            answer_i = self.answers[key_i][1]  # boolean value
            
            # Check contradictions listed in this question
            for j in question_i["contradicts"]:
                key_j = self._key_for(j)
                if key_j not in self.answers:
                    continue
                
                answer_j = self.answers[key_j][1]
                question_j = self.question_set[j]
                
                # If both are agreed with, that's a contradiction
                # (Both can't be true if they contradict)
                if answer_i and answer_j:
                    contradictions.append((i, j, question_i["text"], question_j["text"]))
        
        return contradictions

    def detect_requirements(self) -> list[tuple[int, int, str, str]]:
        """
        Returns list of (q1_index, q2_index, q1_text, q2_text) for required relationships.
        A requirement exists if:
        - Question i requires question j in its "requires" list
        - Both were answered "Agree" (True)
        """
        requirements = []
        for i in range(len(self.question_set)):
            key_i = self._key_for(i)
            if key_i not in self.answers:
                continue
            
            question_i = self.question_set[i]
            answer_i = self.answers[key_i][1]  # boolean value
            
            # Check requirements listed in this question
            for j in question_i["requires"]:
                key_j = self._key_for(j)
                if key_j not in self.answers:
                    continue
                
                answer_j = self.answers[key_j][1]
                question_j = self.question_set[j]
                
                # If both are agreed with, that's a valid requirement relationship
                if answer_i and answer_j:
                    requirements.append((i, j, question_i["text"], question_j["text"]))
        
        return requirements


class SurveyApp(toga.App):
    def startup(self):
        self.selected_question_set: Optional[str] = None  # Track selected question set
        self.controller: Optional[SurveyController] = None  # Will be created when set is selected
        self.showing_truth_web = False  # Track which view we're showing
        self.on_home_screen = True  # Start on home screen
        self.survey_started = False  # Track if survey has been started
        self.resolving_contradictions = False  # Track if we're in contradiction resolution mode
        self.contradiction_resolution_index = 0  # Track which contradiction we're resolving
        self.contradictions_to_resolve: list[tuple[int, int, str, str]] = []  # Store contradictions to resolve
        self.selected_question_to_change: Optional[int] = None  # Track which question user wants to change

        self.main_window = toga.MainWindow(title=self.formal_name)
        self._show_current_screen()
        self.main_window.show()

    # UI builders
    def _show_current_screen(self) -> None:
        print(f"DEBUG _show_current_screen: on_home={self.on_home_screen}, controller={self.controller is not None}, resolving={self.resolving_contradictions}, showing_truth_web={self.showing_truth_web}, complete={self.controller.is_complete() if self.controller else False}")
        if self.on_home_screen or self.controller is None:
            self.main_window.content = self._build_home_screen()
        elif self.resolving_contradictions:
            print("DEBUG: Showing contradiction resolution screen")
            if self.selected_question_to_change is not None:
                # Show the question to change answer
                self.main_window.content = self._build_change_answer_screen()
            else:
                # Show contradiction pair selection
                self.main_window.content = self._build_contradiction_resolution_screen()
        elif self.controller.is_complete():
            if self.showing_truth_web:
                self.main_window.content = self._build_truth_web_screen()
            else:
                self.main_window.content = self._build_results_screen()
        else:
            self.showing_truth_web = False  # Reset when not complete
            self.main_window.content = self._build_question_screen()
    
    def _get_question_set_status(self, question_set_name: str) -> str:
        """Get status of a question set: 'not_started', 'in_progress', or 'completed'"""
        # Create a temporary controller to check status
        temp_controller = SurveyController(self, question_set_name)
        if len(temp_controller.answers) == 0:
            return "not_started"
        elif temp_controller.is_complete():
            return "completed"
        else:
            return "in_progress"
    
    def _build_home_screen(self) -> toga.Box:
        """Build the home/welcome screen with question set selection"""
        root = toga.Box(style=Pack(direction=COLUMN, alignment=CENTER, padding=32))
        
        # App title
        title = toga.Label(
            "Survey App",
            style=Pack(padding=(0, 0, 32, 0), font_size=32, font_weight="bold")
        )
        root.add(title)
        
        # Question set selection buttons
        button_container = toga.Box(style=Pack(direction=COLUMN, padding_top=16))
        
        # Create buttons for each question set
        for set_name in QUESTION_SETS.keys():
            status = self._get_question_set_status(set_name)
            
            # Create button with appropriate label based on status
            if status == "not_started":
                button_text = set_name
            elif status == "in_progress":
                button_text = f"{set_name} (Continue)"
            else:  # completed
                button_text = f"{set_name} (Review)"
            
            def make_handler(name: str):
                return lambda widget: self._on_select_question_set(name)
            
            set_btn = toga.Button(
                button_text,
                style=Pack(padding=12, width=200, margin_bottom=8),
                on_press=make_handler(set_name)
            )
            button_container.add(set_btn)
        
        root.add(button_container)
        
        return root
    
    def _on_select_question_set(self, question_set_name: str) -> None:
        """Handle question set selection from home screen"""
        self.selected_question_set = question_set_name
        self.controller = SurveyController(self, question_set_name)
        self.on_home_screen = False
        self.survey_started = True
        self.showing_truth_web = False
        self._show_current_screen()
    
    def _on_start_survey(self, widget: Optional[toga.Widget]) -> None:
        """Start the survey from home screen (deprecated - use _on_select_question_set)"""
        # This method is kept for backward compatibility but shouldn't be called
        if self.selected_question_set:
            self._on_select_question_set(self.selected_question_set)
    
    def _on_continue_survey(self, widget: Optional[toga.Widget]) -> None:
        """Continue existing survey"""
        self.on_home_screen = False
        self.survey_started = True
        self._show_current_screen()
    
    def _on_start_over(self, widget: Optional[toga.Widget]) -> None:
        """Start survey over from home screen"""
        if self.controller:
            self.controller.restart()
        self.on_home_screen = False
        self.survey_started = True
        self.showing_truth_web = False
        self._show_current_screen()

    def _build_question_screen(self) -> toga.Box:
        if self.controller is None:
            return self._build_home_screen()
        
        idx = self.controller.current_index
        total = len(self.controller.question_set)
        question_data = self.controller.question_set[idx]
        question_text = question_data["text"]

        root = toga.Box(style=Pack(direction=COLUMN, alignment=CENTER, padding=16))
        progress = toga.Label(f"Question {idx + 1} of {total}", style=Pack(padding=(0, 0, 12, 0)))
        question = toga.Label(question_text, style=Pack(padding=8))

        buttons = toga.Box(style=Pack(direction=ROW, padding_top=12))
        agree_btn = toga.Button("Agree", style=Pack(padding=8), on_press=lambda w: self._on_answer(True))
        disagree_btn = toga.Button("Disagree", style=Pack(padding=8), on_press=lambda w: self._on_answer(False))
        buttons.add(agree_btn)
        buttons.add(disagree_btn)

        root.add(progress)
        root.add(question)
        root.add(buttons)
        return root

    def _on_answer(self, value: bool) -> None:
        if self.controller is None:
            return
        
        # If we're in contradiction resolution mode, handle differently
        if self.resolving_contradictions and self.selected_question_to_change is not None:
            # Update the answer for the selected question
            key = self.controller._key_for(self.selected_question_to_change)
            question_data = self.controller.question_set[self.selected_question_to_change]
            question_text = question_data["text"]
            self.controller.answers[key] = [question_text, value]
            save_answers(self.controller.responses_path, self.controller.answers)
            
            # Reset selected question
            self.selected_question_to_change = None
            
            # Re-detect all contradictions to get current state (answers may have changed)
            remaining_contradictions = self.controller.detect_contradictions()
            
            if not remaining_contradictions:
                # All contradictions resolved, go back to TruthWeb
                self.resolving_contradictions = False
                self.showing_truth_web = True
            else:
                # Update the list of contradictions to resolve with current state
                self.contradictions_to_resolve = remaining_contradictions
                
                # Check if the contradiction we were working on still exists
                # If it was resolved, we'll automatically move to the next one
                # Reset to 0 to show the first remaining contradiction
                self.contradiction_resolution_index = 0
        else:
            # Normal answer recording
            self.controller.record_answer(value)
        
        self._show_current_screen()

    def _build_results_screen(self) -> toga.Box:
        root = toga.Box(style=Pack(direction=COLUMN, padding=16))
        title = toga.Label("Results", style=Pack(padding=(0, 0, 12, 0)))

        # Answers table
        answers_label = toga.Label("Your Answers:", style=Pack(padding=(0, 0, 8, 0)))
        table = toga.Table(
            headings=["Question", "Answer"],
            accessors=["question", "answer"],
            multiple_select=False,
            style=Pack(flex=1)
        )

        for i in range(len(self.controller.question_set)):
            key = self.controller._key_for(i)
            entry = self.controller.answers.get(key)
            if entry:
                question_text, value = entry
                table.data.append({
                    "question": question_text,
                    "answer": "Agree" if bool(value) else "Disagree",
                })

        root.add(title)
        root.add(answers_label)
        root.add(table)

        # Contradictions section
        contradictions = self.controller.detect_contradictions()
        if contradictions:
            contradictions_label = toga.Label(
                "⚠️ Contradictory Answers Detected:",
                style=Pack(padding=(16, 0, 8, 0))
            )
            root.add(contradictions_label)
            
            contradictions_text = "\n\n".join(
                f"• Question {i+1}: \"{q1}\"\n  contradicts\n  Question {j+1}: \"{q2}\"\n  (You agreed with both)"
                for i, j, q1, q2 in contradictions
            )
            
            contradictions_view = toga.MultilineTextInput(
                value=contradictions_text,
                readonly=True,
                style=Pack(padding=8, flex=1)
            )
            root.add(contradictions_view)
        else:
            no_contradictions = toga.Label(
                "✓ No contradictions detected",
                style=Pack(padding=(16, 0, 8, 0))
            )
            root.add(no_contradictions)

        button_box = toga.Box(style=Pack(direction=ROW, padding_top=12, alignment=CENTER))
        
        truth_web_btn = toga.Button(
            "TruthWeb",
            style=Pack(padding=8, flex=1),
            on_press=self._on_show_truth_web
        )
        
        home_btn = toga.Button(
            "Home",
            style=Pack(padding=8, flex=1),
            on_press=self._on_go_home
        )
        
        restart_btn = toga.Button(
            "Restart",
            style=Pack(padding=8, flex=1),
            on_press=self._on_restart
        )
        
        button_box.add(truth_web_btn)
        button_box.add(home_btn)
        button_box.add(restart_btn)
        root.add(button_box)
        
        return root

    def _on_restart(self, widget: Optional[toga.Widget]) -> None:
        """Restart survey and return to home screen"""
        if self.controller:
            self.controller.restart()
        self.showing_truth_web = False  # Reset view state
        self.on_home_screen = True  # Return to home screen
        self.survey_started = False
        self.selected_question_set = None
        self.controller = None
        self._show_current_screen()
    
    def _on_go_home(self, widget: Optional[toga.Widget]) -> None:
        """Return to home screen"""
        self.showing_truth_web = False
        self.resolving_contradictions = False
        self.selected_question_to_change = None
        self.contradiction_resolution_index = 0
        self.on_home_screen = True
        # Don't reset controller - keep it so we can show status on home screen
        self._show_current_screen()

    def _on_show_truth_web(self, widget: Optional[toga.Widget]) -> None:
        """Switch to TruthWeb view"""
        self.showing_truth_web = True
        self._show_current_screen()

    def _on_back_to_results(self, widget: Optional[toga.Widget]) -> None:
        """Switch back to results view"""
        self.showing_truth_web = False
        self.resolving_contradictions = False
        self.selected_question_to_change = None
        self._show_current_screen()
    
    def _on_start_resolve_contradictions(self, widget: Optional[toga.Widget]) -> None:
        """Start contradiction resolution flow"""
        try:
            print("DEBUG: _on_start_resolve_contradictions called")
            if self.controller is None:
                print("DEBUG: Controller is None")
                self.main_window.info_dialog("Error", "Controller is not available")
                return
            
            contradictions = self.controller.detect_contradictions()
            print(f"DEBUG: Found {len(contradictions)} contradictions")
            
            if not contradictions:
                print("DEBUG: No contradictions found")
                self.main_window.info_dialog("No Contradictions", "There are no contradictions to resolve.")
                return
            
            # Set up contradiction resolution state
            self.contradictions_to_resolve = contradictions
            self.contradiction_resolution_index = 0
            self.resolving_contradictions = True
            self.selected_question_to_change = None
            self.showing_truth_web = False  # Exit truth web mode
            self.on_home_screen = False  # Make sure we're not on home screen
            
            print(f"DEBUG: Starting resolution, contradictions_to_resolve: {len(self.contradictions_to_resolve)}")
            print(f"DEBUG: State - resolving: {self.resolving_contradictions}, showing_truth_web: {self.showing_truth_web}, on_home: {self.on_home_screen}")
            
            # Force screen refresh
            self._show_current_screen()
        except Exception as e:
            print(f"DEBUG: Error in _on_start_resolve_contradictions: {e}")
            import traceback
            traceback.print_exc()
            self.main_window.info_dialog("Error", f"Error starting contradiction resolution: {str(e)}")

    def _build_truth_web_screen(self) -> toga.Box:
        """Build the TruthWeb visualization screen with graph image"""
        if self.controller is None:
            return self._build_home_screen()
        
        root = toga.Box(style=Pack(direction=COLUMN, padding=0))
        
        # Title and back button
        header = toga.Box(style=Pack(direction=ROW, padding=8))
        title = toga.Label("TruthWeb", style=Pack(padding=8, flex=1))
        back_btn = toga.Button(
            "← Back",
            style=Pack(padding=8),
            on_press=self._on_back_to_results
        )
        home_btn = toga.Button(
            "Home",
            style=Pack(padding=8),
            on_press=self._on_go_home
        )
        header.add(title)
        header.add(back_btn)
        header.add(home_btn)
        root.add(header)
        
        # Check for contradictions and add resolve button below header
        contradictions = self.controller.detect_contradictions()
        if contradictions:
            resolve_button_box = toga.Box(style=Pack(direction=ROW, padding=8, alignment=CENTER))
            resolve_btn = toga.Button(
                f"Resolve Contradictions ({len(contradictions)})",
                style=Pack(padding=12, flex=1),
                on_press=self._on_start_resolve_contradictions
            )
            resolve_button_box.add(resolve_btn)
            root.add(resolve_button_box)
        
        # Create scrollable container for the graph
        scroll = toga.ScrollContainer(style=Pack(flex=1))
        content_box = toga.Box(style=Pack(direction=COLUMN, padding=16))
        
        # Legend
        legend = toga.Label(
            "🔴 Red = Contradictions | 🟢 Green = Requirements\n"
            "🔵 Blue = Agreed | ⚪ Gray = Disagreed/Unanswered\n"
            "Tap a node to see question details",
            style=Pack(padding=(0, 0, 16, 0))
        )
        content_box.add(legend)
        
        # Generate and display graph
        if PILLOW_AVAILABLE:
            try:
                # Generate image and get node positions for click handling
                result = self._generate_graph_image()
                if result:
                    graph_image_path, node_positions = result
                    if graph_image_path and graph_image_path.exists():
                        # Always use WebView for interactive graph (clickable nodes)
                        # Fallback to image with buttons if WebView fails
                        use_webview = False
                        try:
                            # Create interactive HTML with Canvas
                            interactive_html = self._create_interactive_graph_html(node_positions)
                            
                            # Save HTML to file first (file:// URLs are more reliable than data:// on Android)
                            html_file_path = self.paths.data / 'truthweb_interactive.html'
                            html_file_path.parent.mkdir(parents=True, exist_ok=True)
                            html_file_path.write_text(interactive_html, encoding='utf-8')
                            
                            # Try WebView with file:// URL
                            file_url = html_file_path.as_uri()
                            
                            webview = toga.WebView(
                                style=Pack(flex=1, width=600, height=600),
                                url=file_url
                            )
                            content_box.add(webview)
                            use_webview = True
                        except Exception as e:
                            # WebView failed, use image fallback
                            import traceback
                            print(f"WebView failed: {e}")
                            traceback.print_exc()
                            use_webview = False
                        
                        if not use_webview:
                            # Fallback: Use Pillow image with clickable buttons below
                            self._add_image_with_clickable_buttons(content_box, graph_image_path, node_positions)
                    else:
                        error_label = toga.Label(
                            "Could not generate graph image",
                            style=Pack(padding=16)
                        )
                        content_box.add(error_label)
                else:
                    error_label = toga.Label(
                        "Could not generate graph image",
                        style=Pack(padding=16)
                    )
                    content_box.add(error_label)
            except Exception as e:
                error_label = toga.Label(
                    f"Error generating graph: {str(e)}",
                    style=Pack(padding=16)
                )
                content_box.add(error_label)
        else:
            error_label = toga.Label(
                "Pillow is not available. Please install Pillow.",
                style=Pack(padding=16)
            )
            content_box.add(error_label)
        
        scroll.content = content_box
        root.add(scroll)
        
        return root
    
    def _add_image_with_clickable_buttons(self, container: toga.Box, image_path: Path, node_positions: List[Tuple[float, float]]):
        """Add image with clickable number buttons (fallback when WebView doesn't work)"""
        if self.controller is None:
            return
        
        # Image display size
        display_width = 600
        display_height = 600
        
        # Add the graph image
        image_view = toga.ImageView(
            image=image_path,
            style=Pack(width=display_width, height=display_height)
        )
        container.add(image_view)
        
        # Add instruction - make it very clear
        instruction = toga.Label(
            "⚠️ Tap the question buttons below to see details for each node:",
            style=Pack(padding=(12, 0, 8, 0), font_weight="bold")
        )
        container.add(instruction)
        
        # Create clickable number buttons in a row matching the graph nodes
        buttons_label = toga.Label(
            "Quick Access (tap to view question):",
            style=Pack(padding=(0, 0, 8, 0))
        )
        container.add(buttons_label)
        
        # Create buttons row - wrap them if needed
        buttons_row = toga.Box(style=Pack(direction=ROW, padding=4, alignment=CENTER, flex_wrap="wrap"))
        
        for i in range(len(self.controller.question_set)):
            def make_handler(q_idx: int):
                return lambda widget: self._on_question_click(q_idx)
            
            # Color button based on answer status
            key = self.controller._key_for(i)
            answered = key in self.controller.answers
            if answered:
                agreed = self.controller.answers[key][1]
                button_text = f"🔵 Q{i+1}" if agreed else f"⚪ Q{i+1}"
            else:
                button_text = f"⚪ Q{i+1}"
            
            node_btn = toga.Button(
                button_text,
                style=Pack(padding=8, width=70, height=45),
                on_press=make_handler(i)
            )
            buttons_row.add(node_btn)
        
        container.add(buttons_row)
        
        # Also add the full question list for easier access
        questions_label = toga.Label(
            "Full Question List (tap to view details):",
            style=Pack(padding=(16, 0, 8, 0))
        )
        container.add(questions_label)
        
        # Create clickable buttons for each question with full text
        for i in range(len(self.controller.question_set)):
            key = self.controller._key_for(i)
            answered = key in self.controller.answers
            agreed = False
            status = "⚪"
            if answered:
                agreed = self.controller.answers[key][1]
                status = "🔵" if agreed else "⚪"
            
            question_text = self.controller.question_set[i]['text']
            # Truncate for button label
            short_text = question_text[:50] + "..." if len(question_text) > 50 else question_text
            
            def make_click_handler(q_idx: int):
                return lambda widget: self._on_question_click(q_idx)
            
            question_btn = toga.Button(
                f"{status} Q{i+1}: {short_text}",
                style=Pack(padding=6),
                on_press=make_click_handler(i)
            )
            container.add(question_btn)
    
    def _build_contradiction_resolution_screen(self) -> toga.Box:
        """Build screen showing two contradictory questions to resolve"""
        print(f"DEBUG: Building contradiction resolution screen, controller: {self.controller is not None}, contradictions: {len(self.contradictions_to_resolve) if self.contradictions_to_resolve else 0}")
        if self.controller is None:
            print("DEBUG: No controller, returning home")
            return self._build_home_screen()
        if not self.contradictions_to_resolve:
            print("DEBUG: No contradictions to resolve, returning home")
            return self._build_home_screen()
        
        if self.contradiction_resolution_index >= len(self.contradictions_to_resolve):
            # All contradictions resolved
            print("DEBUG: All contradictions resolved, returning to TruthWeb")
            self.resolving_contradictions = False
            self.showing_truth_web = True
            return self._build_truth_web_screen()
        
        print(f"DEBUG: Showing contradiction {self.contradiction_resolution_index + 1} of {len(self.contradictions_to_resolve)}")
        
        root = toga.Box(style=Pack(direction=COLUMN, padding=0))
        
        # Header with progress and back button (fixed at top)
        header = toga.Box(style=Pack(direction=ROW, padding=8))
        progress_label = toga.Label(
            f"Resolving Contradictions ({self.contradiction_resolution_index + 1} of {len(self.contradictions_to_resolve)})",
            style=Pack(padding=8, flex=1, font_weight="bold")
        )
        cancel_btn = toga.Button(
            "Cancel",
            style=Pack(padding=8),
            on_press=self._on_cancel_resolve_contradictions
        )
        header.add(progress_label)
        header.add(cancel_btn)
        root.add(header)
        
        # Scrollable content area
        scroll = toga.ScrollContainer(style=Pack(flex=1))
        content_box = toga.Box(style=Pack(direction=COLUMN, padding=16))
        
        # Get current contradiction
        q1_idx, q2_idx, q1_text, q2_text = self.contradictions_to_resolve[self.contradiction_resolution_index]
        
        # Get current answers
        key1 = self.controller._key_for(q1_idx)
        key2 = self.controller._key_for(q2_idx)
        answer1 = self.controller.answers.get(key1, [None, None])[1] if key1 in self.controller.answers else None
        answer2 = self.controller.answers.get(key2, [None, None])[1] if key2 in self.controller.answers else None
        
        answer1_text = "Agree" if answer1 else "Disagree"
        answer2_text = "Agree" if answer2 else "Disagree"
        
        # Instruction
        instruction = toga.Label(
            "You agreed with both of these contradictory statements.\n"
            "Select which answer you want to change:",
            style=Pack(padding=(0, 0, 16, 0), text_align=CENTER)
        )
        content_box.add(instruction)
        
        # Question 1 box
        q1_box = toga.Box(style=Pack(direction=COLUMN, padding=12, margin_bottom=8))
        q1_header = toga.Label(
            f"Question {q1_idx + 1}:",
            style=Pack(padding=(0, 0, 8, 0), font_weight="bold")
        )
        q1_text_label = toga.Label(
            q1_text,
            style=Pack(padding=(0, 0, 8, 0))
        )
        q1_answer_label = toga.Label(
            f"Your Answer: {answer1_text}",
            style=Pack(padding=(0, 0, 8, 0), font_weight="bold")
        )
        change_q1_btn = toga.Button(
            f"Change Answer to Question {q1_idx + 1}",
            style=Pack(padding=12),
            on_press=lambda w: self._on_select_question_to_change(q1_idx)
        )
        q1_box.add(q1_header)
        q1_box.add(q1_text_label)
        q1_box.add(q1_answer_label)
        q1_box.add(change_q1_btn)
        content_box.add(q1_box)
        
        # Divider
        divider = toga.Label(
            "VS",
            style=Pack(padding=8, font_weight="bold", font_size=18)
        )
        content_box.add(divider)
        
        # Question 2 box
        q2_box = toga.Box(style=Pack(direction=COLUMN, padding=12, margin_bottom=8))
        q2_header = toga.Label(
            f"Question {q2_idx + 1}:",
            style=Pack(padding=(0, 0, 8, 0), font_weight="bold")
        )
        q2_text_label = toga.Label(
            q2_text,
            style=Pack(padding=(0, 0, 8, 0))
        )
        q2_answer_label = toga.Label(
            f"Your Answer: {answer2_text}",
            style=Pack(padding=(0, 0, 8, 0), font_weight="bold")
        )
        change_q2_btn = toga.Button(
            f"Change Answer to Question {q2_idx + 1}",
            style=Pack(padding=12),
            on_press=lambda w: self._on_select_question_to_change(q2_idx)
        )
        q2_box.add(q2_header)
        q2_box.add(q2_text_label)
        q2_box.add(q2_answer_label)
        q2_box.add(change_q2_btn)
        content_box.add(q2_box)
        
        scroll.content = content_box
        root.add(scroll)
        
        return root
    
    def _build_change_answer_screen(self) -> toga.Box:
        """Build screen to change answer for a specific question"""
        if self.controller is None or self.selected_question_to_change is None:
            return self._build_contradiction_resolution_screen()
        
        root = toga.Box(style=Pack(direction=COLUMN, alignment=CENTER, padding=16))
        
        q_idx = self.selected_question_to_change
        question_data = self.controller.question_set[q_idx]
        question_text = question_data["text"]
        
        # Get current answer
        key = self.controller._key_for(q_idx)
        current_answer = None
        if key in self.controller.answers:
            current_answer = self.controller.answers[key][1]
        
        # Header
        header_label = toga.Label(
            f"Change Answer for Question {q_idx + 1}",
            style=Pack(padding=(0, 0, 16, 0), font_weight="bold", font_size=18)
        )
        root.add(header_label)
        
        # Question text
        question_label = toga.Label(
            question_text,
            style=Pack(padding=(0, 0, 24, 0))
        )
        root.add(question_label)
        
        # Current answer
        current_answer_text = "Agree" if current_answer else "Disagree"
        current_label = toga.Label(
            f"Current Answer: {current_answer_text}",
            style=Pack(padding=(0, 0, 16, 0), font_weight="bold")
        )
        root.add(current_label)
        
        # New answer options
        instruction = toga.Label(
            "Select your new answer:",
            style=Pack(padding=(0, 0, 12, 0))
        )
        root.add(instruction)
        
        buttons = toga.Box(style=Pack(direction=ROW, padding_top=12))
        agree_btn = toga.Button(
            "Agree",
            style=Pack(padding=12, width=150),
            on_press=lambda w: self._on_answer(True)
        )
        disagree_btn = toga.Button(
            "Disagree",
            style=Pack(padding=12, width=150),
            on_press=lambda w: self._on_answer(False)
        )
        buttons.add(agree_btn)
        buttons.add(disagree_btn)
        root.add(buttons)
        
        # Cancel button
        cancel_btn = toga.Button(
            "Cancel",
            style=Pack(padding=12, margin_top=16, width=150),
            on_press=self._on_cancel_change_answer
        )
        root.add(cancel_btn)
        
        return root
    
    def _on_select_question_to_change(self, question_index: int) -> None:
        """Handle selection of which question to change in contradiction resolution"""
        self.selected_question_to_change = question_index
        self._show_current_screen()
    
    def _on_cancel_change_answer(self, widget: Optional[toga.Widget]) -> None:
        """Cancel changing answer and go back to contradiction selection"""
        self.selected_question_to_change = None
        self._show_current_screen()
    
    def _on_cancel_resolve_contradictions(self, widget: Optional[toga.Widget]) -> None:
        """Cancel contradiction resolution and return to TruthWeb"""
        self.resolving_contradictions = False
        self.selected_question_to_change = None
        self.contradiction_resolution_index = 0
        self.showing_truth_web = True
        self._show_current_screen()
    
    def _create_interactive_graph_html(self, node_positions: List[Tuple[float, float]]) -> str:
        """Create HTML with clickable graph using Canvas"""
        if self.controller is None:
            return ""
        
        import json
        
        # Prepare data - scale node positions from 800x800 image to 600x600 canvas
        scale_factor = 600.0 / 800.0  # Scale from 800px image to 600px canvas
        nodes = []
        for i in range(len(self.controller.question_set)):
            key = self.controller._key_for(i)
            answered = key in self.controller.answers
            agreed = False
            if answered:
                agreed = self.controller.answers[key][1]
            # Scale positions to match 600x600 canvas
            orig_x, orig_y = node_positions[i]
            scaled_x = orig_x * scale_factor
            scaled_y = orig_y * scale_factor
            nodes.append({
                'index': i,
                'answered': answered,
                'agreed': agreed,
                'x': scaled_x,
                'y': scaled_y
            })
        
        contradictions = [[i, j] for i, j, _, _ in self.controller.detect_contradictions()]
        requirements = [[i, j] for i, j, _, _ in self.controller.detect_requirements()]
        
        # Create JavaScript data
        questions_data = [q['text'] for q in self.controller.question_set]
        questions_js = json.dumps(questions_data, ensure_ascii=False)
        nodes_js = json.dumps(nodes, ensure_ascii=False)
        contradictions_js = json.dumps(contradictions, ensure_ascii=False)
        requirements_js = json.dumps(requirements, ensure_ascii=False)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TruthWeb</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ margin: 0; padding: 8px; background: white; font-family: Arial, sans-serif; }}
        #canvasContainer {{ text-align: center; margin: 8px 0; }}
        canvas {{ border: 1px solid #ddd; max-width: 100%; height: auto; display: block; margin: 0 auto; }}
        #info {{ padding: 12px; background: #f0f0f0; margin-top: 8px; border-radius: 4px; font-size: 14px; min-height: 60px; line-height: 1.5; }}
        #info strong {{ color: #333; display: block; margin-bottom: 4px; }}
    </style>
</head>
<body>
    <div id="canvasContainer">
        <canvas id="graphCanvas" width="600" height="600"></canvas>
    </div>
    <div id="info">Tap a node (Q1-Q10) on the graph above to see question details</div>
    <script>
        const canvas = document.getElementById('graphCanvas');
        const ctx = canvas.getContext('2d');
        const info = document.getElementById('info');
        
        const questions = {questions_js};
        const nodes = {nodes_js};
        const contradictions = {contradictions_js};
        const requirements = {requirements_js};
        
        const width = 600;
        const height = 600;
        const nodeRadius = 30;
        
        function drawGraph() {{
            // Clear canvas
            ctx.fillStyle = 'white';
            ctx.fillRect(0, 0, width, height);
            
            // Draw connections first (so they appear behind nodes)
            // Draw contradictions in red
            contradictions.forEach(([i, j]) => {{
                if (i < nodes.length && j < nodes.length) {{
                    const n1 = nodes[i];
                    const n2 = nodes[j];
                    ctx.strokeStyle = '#d32f2f';
                    ctx.lineWidth = 4;
                    ctx.beginPath();
                    ctx.moveTo(n1.x, n1.y);
                    ctx.lineTo(n2.x, n2.y);
                    ctx.stroke();
                }}
            }});
            
            // Draw requirements in green
            requirements.forEach(([i, j]) => {{
                if (i < nodes.length && j < nodes.length) {{
                    const n1 = nodes[i];
                    const n2 = nodes[j];
                    ctx.strokeStyle = '#388e3c';
                    ctx.lineWidth = 4;
                    ctx.beginPath();
                    ctx.moveTo(n1.x, n1.y);
                    ctx.lineTo(n2.x, n2.y);
                    ctx.stroke();
                }}
            }});
            
            // Draw nodes
            nodes.forEach(node => {{
                let fillColor = '#e0e0e0';  // Light gray for unanswered
                let strokeColor = '#999999';
                if (node.answered) {{
                    if (node.agreed) {{
                        fillColor = '#4a90e2';  // Blue for agreed
                        strokeColor = '#2d5aa0';
                    }} else {{
                        fillColor = '#cccccc';  // Gray for disagreed
                        strokeColor = '#888888';
                    }}
                }}
                
                // Draw circle
                ctx.fillStyle = fillColor;
                ctx.strokeStyle = strokeColor;
                ctx.lineWidth = 3;
                ctx.beginPath();
                ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI);
                ctx.fill();
                ctx.stroke();
                
                // Draw question number
                ctx.fillStyle = 'white';
                ctx.font = 'bold 16px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText('Q' + (node.index + 1), node.x, node.y);
            }});
        }}
        
        // Handle clicks and touches
        function getCanvasCoordinates(e) {{
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            
            let clientX, clientY;
            if (e.touches && e.touches.length > 0) {{
                // Touch event
                clientX = e.touches[0].clientX;
                clientY = e.touches[0].clientY;
            }} else if (e.changedTouches && e.changedTouches.length > 0) {{
                // Touch end event
                clientX = e.changedTouches[0].clientX;
                clientY = e.changedTouches[0].clientY;
            }} else {{
                // Mouse/click event
                clientX = e.clientX;
                clientY = e.clientY;
            }}
            
            const x = (clientX - rect.left) * scaleX;
            const y = (clientY - rect.top) * scaleY;
            return {{x: x, y: y}};
        }}
        
        function handleInteraction(e) {{
            e.preventDefault();
            e.stopPropagation();
            
            const coords = getCanvasCoordinates(e);
            const x = coords.x;
            const y = coords.y;
            
            // Find which node was clicked
            for (let i = 0; i < nodes.length; i++) {{
                const node = nodes[i];
                const dx = x - node.x;
                const dy = y - node.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance <= nodeRadius + 5) {{
                    const answered = node.answered;
                    const agreed = node.agreed;
                    const answerText = answered ? (agreed ? 'Agree' : 'Disagree') : 'Not answered';
                    const questionText = questions[node.index];
                    const qNum = node.index + 1;
                    
                    // Update info display
                    info.innerHTML = '<strong>Question ' + qNum + ':</strong>' + 
                                   '<br>' + questionText + 
                                   '<br><br><strong>Your Answer:</strong> ' + answerText;
                    
                    // Show alert as well for visibility
                    setTimeout(function() {{
                        alert('Question ' + qNum + ':\\n\\n' + questionText + '\\n\\nYour Answer: ' + answerText);
                    }}, 50);
                    break;
                }}
            }}
        }}
        
        canvas.addEventListener('click', handleInteraction);
        canvas.addEventListener('touchend', handleInteraction);
        canvas.addEventListener('touchstart', function(e) {{ e.preventDefault(); }});
        
        // Initial draw
        drawGraph();
    </script>
</body>
</html>"""
        return html
    
    def _create_clickable_graph_html(self, node_positions: List[Tuple[float, float]]) -> str:
        """Create a simple HTML file (placeholder)"""
        return ""
    
    def _on_question_click(self, question_index: int):
        """Show a dialog with question details when a question is clicked"""
        if self.controller is None:
            return
        
        question_data = self.controller.question_set[question_index]
        question_text = question_data['text']
        
        key = self.controller._key_for(question_index)
        answered = key in self.controller.answers
        
        if answered:
            agreed = self.controller.answers[key][1]
            answer_text = "Agree" if agreed else "Disagree"
        else:
            answer_text = "Not answered"
        
        # Create dialog content
        dialog_content = f"Question {question_index + 1}:\n\n{question_text}\n\nYour Answer: {answer_text}"
        
        # Show dialog
        self.main_window.info_dialog(
            f"Question {question_index + 1}",
            dialog_content
        )
    
    def _generate_graph_image(self) -> Optional[Tuple[Path, List[Tuple[float, float]]]]:
        """Generate a graph visualization image using Pillow
        Returns: (image_path, node_positions) or None
        """
        if self.controller is None:
            return None
        
        try:
            # Prepare data
            nodes = []
            for i in range(len(self.controller.question_set)):
                key = self.controller._key_for(i)
                answered = key in self.controller.answers
                agreed = False
                if answered:
                    agreed = self.controller.answers[key][1]
                nodes.append({
                    'index': i,
                    'answered': answered,
                    'agreed': agreed
                })
            
            contradictions = self.controller.detect_contradictions()
            requirements = self.controller.detect_requirements()
            
            # Image dimensions - use a standard size that will be scaled by the UI
            # This ensures good quality when scaled up or down
            width = 800
            height = 800
            center_x = width // 2
            center_y = height // 2
            radius = min(width, height) * 0.35  # Circle radius for nodes
            node_radius = 30  # Size of each node
            
            # Create image with white background
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Calculate node positions in circle
            num_nodes = len(self.controller.question_set)
            node_positions = []
            
            for i in range(num_nodes):
                angle = 2 * math.pi * i / num_nodes - math.pi / 2
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                node_positions.append((x, y))
            
            # Draw connections first (so they appear behind nodes)
            # Draw contradictions in red
            for i, j, _, _ in contradictions:
                if i < len(node_positions) and j < len(node_positions):
                    x1, y1 = node_positions[i]
                    x2, y2 = node_positions[j]
                    draw.line([(x1, y1), (x2, y2)], fill='#d32f2f', width=5)
            
            # Draw requirements in green
            for i, j, _, _ in requirements:
                if i < len(node_positions) and j < len(node_positions):
                    x1, y1 = node_positions[i]
                    x2, y2 = node_positions[j]
                    draw.line([(x1, y1), (x2, y2)], fill='#388e3c', width=5)
            
            # Try to load a font, fall back to default if not available
            try:
                font = ImageFont.truetype("Arial.ttf", 16)
                bold_font = ImageFont.truetype("Arial Bold.ttf", 16)
            except:
                try:
                    font = ImageFont.load_default()
                    bold_font = font
                except:
                    font = None
                    bold_font = None
            
            # Draw nodes
            for i, (x, y) in enumerate(node_positions):
                node = nodes[i]
                
                # Node color based on status
                if not node['answered']:
                    fill_color = (224, 224, 224)  # Light gray #e0e0e0
                    outline_color = (153, 153, 153)  # #999999
                elif node['agreed']:
                    fill_color = (74, 144, 226)  # Blue #4a90e2
                    outline_color = (45, 90, 160)  # #2d5aa0
                else:
                    fill_color = (204, 204, 204)  # Gray #cccccc
                    outline_color = (136, 136, 136)  # #888888
                
                # Draw circle for node
                # Pillow draws circles using ellipse with equal width/height
                left = x - node_radius
                top = y - node_radius
                right = x + node_radius
                bottom = y + node_radius
                
                # Draw filled circle
                draw.ellipse([left, top, right, bottom], fill=fill_color, outline=outline_color, width=3)
                
                # Draw question number text
                text = f'Q{i+1}'
                # Get text size to center it
                if font:
                    bbox = draw.textbbox((0, 0), text, font=bold_font or font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                else:
                    text_width = len(text) * 10
                    text_height = 16
                
                text_x = x - text_width // 2
                text_y = y - text_height // 2
                
                draw.text((text_x, text_y), text, fill='white', font=bold_font or font)
            
            # Save to file
            image_path = self.paths.data / 'truthweb_graph.png'
            image_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(image_path, 'PNG')
            
            # Return both image path and node positions for click handling
            return (image_path, node_positions)
            
        except Exception as e:
            print(f"Error generating graph: {e}")
            import traceback
            traceback.print_exc()
            return None



