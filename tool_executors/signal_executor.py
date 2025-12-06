"""
Main Signal tool executor class.

Combines all tool execution mixins into a single class.
"""

import logging
from typing import Callable, Optional

from tool_schemas import ALL_META_CATEGORIES, FINANCE_CATEGORIES, SHEETS_CATEGORIES
from .base import SignalToolExecutorBase
from .basic_tools import BasicToolsMixin
from .finance_executor import FinanceToolsMixin
from .sheets_core import SheetsCoreMixin
from .sheets_advanced import SheetsAdvancedMixin
from .calendar_executor import CalendarTriggersMixin
from .dnd_executor import DndToolsMixin

logger = logging.getLogger(__name__)


class SignalToolExecutor(
    SignalToolExecutorBase,
    BasicToolsMixin,
    FinanceToolsMixin,
    SheetsCoreMixin,
    SheetsAdvancedMixin,
    CalendarTriggersMixin,
    DndToolsMixin
):
    """
    Executes tool calls for the Signal bot.
    Supports image generation, weather, time, wikipedia, finance, emoji reactions, Google Sheets,
    Google Calendar, scheduled triggers, and D&D game master tools.
    
    Inherits implementation methods from mixins:
    - BasicToolsMixin: Weather, time, Wikipedia, dice, reactions
    - FinanceToolsMixin: Stock quotes, news, financials
    - SheetsCoreMixin: Core spreadsheet operations
    - SheetsAdvancedMixin: Charts, pivots, protection, groups
    - CalendarTriggersMixin: Calendar and scheduled triggers
    - DndToolsMixin: D&D campaign management
    """

    def execute(self, function_name: str, arguments: dict) -> dict:
        """
        Execute a tool call for Signal bot.

        Args:
            function_name: Name of the function
            arguments: Dictionary of function arguments

        Returns:
            Dict with 'success' and 'message' keys, or expansion signal for meta-tools
        """
        # Two-phase meta-tool detection
        if function_name in ALL_META_CATEGORIES:
            self.expansion_requested = True
            # Track which group this meta-tool belongs to (use sets to accumulate multiple categories)
            if function_name in FINANCE_CATEGORIES:
                if "finance" not in self.expanded_categories:
                    self.expanded_categories["finance"] = set()
                self.expanded_categories["finance"].add(function_name)
            elif function_name in SHEETS_CATEGORIES:
                if "sheets" not in self.expanded_categories:
                    self.expanded_categories["sheets"] = set()
                self.expanded_categories["sheets"].add(function_name)

            intent = arguments.get("intent", "")
            self.last_meta_intent = intent  # Store for context in retry
            available_tools = ALL_META_CATEGORIES[function_name]["sub_tools"]
            logger.info(f"Meta-tool expansion requested: {function_name} (intent: {intent})")

            return {
                "success": True,
                "expansion_needed": True,
                "category": function_name,
                "intent": intent,
                "available_tools": available_tools,
                "message": f"Expanding {function_name}. Available tools: {', '.join(available_tools)}"
            }

        if function_name == "get_weather":
            return self._execute_weather(arguments)

        # Time tools
        if function_name == "get_datetime":
            return self._execute_get_datetime(arguments)
        if function_name == "get_unix_timestamp":
            return self._execute_get_unix_timestamp(arguments)

        # Wikipedia tools
        if function_name == "search_wikipedia":
            return self._execute_search_wikipedia(arguments)
        if function_name == "get_wikipedia_article":
            return self._execute_get_wikipedia_article(arguments)
        if function_name == "get_random_wikipedia_article":
            return self._execute_random_wikipedia_article(arguments)

        # Finance tools
        if function_name == "get_stock_quote":
            return self._execute_stock_quote(arguments)
        if function_name == "get_stock_news":
            return self._execute_stock_news(arguments)
        if function_name == "search_stocks":
            return self._execute_search_stocks(arguments)
        if function_name == "get_top_stocks":
            return self._execute_top_stocks(arguments)
        if function_name == "get_price_history":
            return self._execute_price_history(arguments)
        if function_name == "get_options":
            return self._execute_options(arguments)
        if function_name == "get_earnings":
            return self._execute_earnings(arguments)
        if function_name == "get_analyst_ratings":
            return self._execute_analyst_ratings(arguments)
        if function_name == "get_dividends":
            return self._execute_dividends(arguments)
        if function_name == "get_financials":
            return self._execute_financials(arguments)
        if function_name == "get_holders":
            return self._execute_holders(arguments)

        # Reaction tool
        if function_name == "react_to_message":
            return self._execute_react_to_message(arguments)

        # Google Sheets tools
        if function_name == "create_spreadsheet":
            return self._execute_create_spreadsheet(arguments)
        if function_name == "list_spreadsheets":
            return self._execute_list_spreadsheets(arguments)
        if function_name == "read_sheet":
            return self._execute_read_sheet(arguments)
        if function_name == "write_to_sheet":
            return self._execute_write_to_sheet(arguments)
        if function_name == "add_row_to_sheet":
            return self._execute_add_row_to_sheet(arguments)
        if function_name == "search_sheets":
            return self._execute_search_sheets(arguments)
        if function_name == "format_columns":
            return self._execute_format_columns(arguments)
        if function_name == "clear_range":
            return self._execute_clear_range(arguments)
        if function_name == "delete_rows":
            return self._execute_delete_rows(arguments)
        if function_name == "delete_columns":
            return self._execute_delete_columns(arguments)
        if function_name == "insert_rows":
            return self._execute_insert_rows(arguments)
        if function_name == "insert_columns":
            return self._execute_insert_columns(arguments)
        if function_name == "add_sheet":
            return self._execute_add_sheet(arguments)
        if function_name == "delete_sheet":
            return self._execute_delete_sheet(arguments)
        if function_name == "rename_sheet":
            return self._execute_rename_sheet(arguments)
        if function_name == "freeze_rows":
            return self._execute_freeze_rows(arguments)
        if function_name == "freeze_columns":
            return self._execute_freeze_columns(arguments)
        if function_name == "sort_range":
            return self._execute_sort_range(arguments)
        if function_name == "auto_resize_columns":
            return self._execute_auto_resize_columns(arguments)
        if function_name == "merge_cells":
            return self._execute_merge_cells(arguments)
        if function_name == "unmerge_cells":
            return self._execute_unmerge_cells(arguments)
        if function_name == "conditional_format":
            return self._execute_conditional_format(arguments)
        if function_name == "data_validation":
            return self._execute_data_validation(arguments)
        if function_name == "alternating_colors":
            return self._execute_alternating_colors(arguments)
        if function_name == "add_note":
            return self._execute_add_note(arguments)
        if function_name == "set_borders":
            return self._execute_set_borders(arguments)
        if function_name == "set_alignment":
            return self._execute_set_alignment(arguments)
        if function_name == "create_chart":
            return self._execute_create_chart(arguments)
        if function_name == "list_charts":
            return self._execute_list_charts(arguments)
        if function_name == "update_chart":
            return self._execute_update_chart(arguments)
        if function_name == "delete_chart":
            return self._execute_delete_chart(arguments)
        if function_name == "create_pivot_table":
            return self._execute_create_pivot_table(arguments)
        if function_name == "delete_pivot_table":
            return self._execute_delete_pivot_table(arguments)

        # Text formatting & color tools (Batch 1)
        if function_name == "set_text_format":
            return self._execute_set_text_format(arguments)
        if function_name == "set_text_color":
            return self._execute_set_text_color(arguments)
        if function_name == "set_background_color":
            return self._execute_set_background_color(arguments)
        if function_name == "add_hyperlink":
            return self._execute_add_hyperlink(arguments)

        # Filtering tools (Batch 2)
        if function_name == "set_basic_filter":
            return self._execute_set_basic_filter(arguments)
        if function_name == "clear_basic_filter":
            return self._execute_clear_basic_filter(arguments)
        if function_name == "create_filter_view":
            return self._execute_create_filter_view(arguments)
        if function_name == "delete_filter_view":
            return self._execute_delete_filter_view(arguments)

        # Named & protected range tools (Batch 3)
        if function_name == "create_named_range":
            return self._execute_create_named_range(arguments)
        if function_name == "delete_named_range":
            return self._execute_delete_named_range(arguments)
        if function_name == "list_named_ranges":
            return self._execute_list_named_ranges(arguments)
        if function_name == "protect_range":
            return self._execute_protect_range(arguments)

        # Find/Replace & Copy/Paste tools (Batch 4)
        if function_name == "find_replace":
            return self._execute_find_replace(arguments)
        if function_name == "copy_paste":
            return self._execute_copy_paste(arguments)
        if function_name == "cut_paste":
            return self._execute_cut_paste(arguments)

        # Spreadsheet Properties tools (Batch 8)
        if function_name == "set_spreadsheet_timezone":
            return self._execute_set_spreadsheet_timezone(arguments)
        if function_name == "set_spreadsheet_locale":
            return self._execute_set_spreadsheet_locale(arguments)
        if function_name == "set_recalculation_interval":
            return self._execute_set_recalculation_interval(arguments)
        if function_name == "get_spreadsheet_properties":
            return self._execute_get_spreadsheet_properties(arguments)
        if function_name == "set_spreadsheet_theme":
            return self._execute_set_spreadsheet_theme(arguments)

        # Developer Metadata tools (Batch 9)
        if function_name == "set_developer_metadata":
            return self._execute_set_developer_metadata(arguments)
        if function_name == "get_developer_metadata":
            return self._execute_get_developer_metadata(arguments)
        if function_name == "delete_developer_metadata":
            return self._execute_delete_developer_metadata(arguments)

        # Additional Cell Formatting tools (Batch 10)
        if function_name == "set_text_direction":
            return self._execute_set_text_direction(arguments)
        if function_name == "set_text_rotation":
            return self._execute_set_text_rotation(arguments)
        if function_name == "set_cell_padding":
            return self._execute_set_cell_padding(arguments)
        if function_name == "set_rich_text":
            return self._execute_set_rich_text(arguments)

        # Sheet properties extension tools
        if function_name == "hide_sheet":
            return self._execute_hide_sheet(arguments)
        if function_name == "show_sheet":
            return self._execute_show_sheet(arguments)
        if function_name == "set_tab_color":
            return self._execute_set_tab_color(arguments)
        if function_name == "set_right_to_left":
            return self._execute_set_right_to_left(arguments)
        if function_name == "get_sheet_properties":
            return self._execute_get_sheet_properties(arguments)

        # Protected ranges management tools
        if function_name == "list_protected_ranges":
            return self._execute_list_protected_ranges(arguments)
        if function_name == "update_protected_range":
            return self._execute_update_protected_range(arguments)
        if function_name == "delete_protected_range":
            return self._execute_delete_protected_range(arguments)
        if function_name == "protect_sheet":
            return self._execute_protect_sheet(arguments)

        # Filter views
        if function_name == "list_filter_views":
            return self._execute_list_filter_views(arguments)

        # Dimension groups (row/column grouping)
        if function_name == "create_row_group":
            return self._execute_create_row_group(arguments)
        if function_name == "create_column_group":
            return self._execute_create_column_group(arguments)
        if function_name == "delete_row_group":
            return self._execute_delete_row_group(arguments)
        if function_name == "delete_column_group":
            return self._execute_delete_column_group(arguments)
        if function_name == "collapse_expand_group":
            return self._execute_collapse_expand_group(arguments)
        if function_name == "set_group_control_position":
            return self._execute_set_group_control_position(arguments)

        # Slicers
        if function_name == "list_slicers":
            return self._execute_list_slicers(arguments)
        if function_name == "create_slicer":
            return self._execute_create_slicer(arguments)
        if function_name == "update_slicer":
            return self._execute_update_slicer(arguments)
        if function_name == "delete_slicer":
            return self._execute_delete_slicer(arguments)

        # Tables
        if function_name == "list_tables":
            return self._execute_list_tables(arguments)
        if function_name == "create_table":
            return self._execute_create_table(arguments)
        if function_name == "delete_table":
            return self._execute_delete_table(arguments)
        if function_name == "update_table_column":
            return self._execute_update_table_column(arguments)

        # Google Calendar tools
        if function_name == "create_calendar":
            return self._execute_create_calendar(arguments)
        if function_name == "list_calendars":
            return self._execute_list_calendars(arguments)
        if function_name == "list_events":
            return self._execute_list_events(arguments)
        if function_name == "get_event":
            return self._execute_get_event(arguments)
        if function_name == "create_event":
            return self._execute_create_event(arguments)
        if function_name == "update_event":
            return self._execute_update_event(arguments)
        if function_name == "delete_event":
            return self._execute_delete_event(arguments)
        if function_name == "quick_add_event":
            return self._execute_quick_add_event(arguments)
        if function_name == "share_calendar":
            return self._execute_share_calendar(arguments)

        # Member memory tools
        if function_name == "save_member_memory":
            return self._execute_save_member_memory(arguments)
        if function_name == "get_member_memories":
            return self._execute_get_member_memories(arguments)
        if function_name == "list_group_members":
            return self._execute_list_group_members(arguments)

        # Trigger tools
        if function_name == "create_trigger":
            return self._execute_create_trigger(arguments)
        if function_name == "list_triggers":
            return self._execute_list_triggers(arguments)
        if function_name == "cancel_trigger":
            return self._execute_cancel_trigger(arguments)
        if function_name == "update_trigger":
            return self._execute_update_trigger(arguments)

        # Dice rolling tool
        if function_name == "roll_dice":
            return self._execute_roll_dice(arguments)

        # D&D Game Master tools
        if function_name == "start_dnd_campaign":
            return self._execute_start_dnd_campaign(arguments)
        if function_name == "get_campaign_state":
            return self._execute_get_campaign_state(arguments)
        if function_name == "update_campaign_state":
            return self._execute_update_campaign_state(arguments)
        if function_name == "create_character":
            return self._execute_create_character(arguments)
        if function_name == "update_character":
            return self._execute_update_character(arguments)
        if function_name == "start_combat":
            return self._execute_start_combat(arguments)
        if function_name == "end_combat":
            return self._execute_end_combat(arguments)
        if function_name == "add_npc":
            return self._execute_add_npc(arguments)
        if function_name == "add_location":
            return self._execute_add_location(arguments)
        if function_name == "list_campaigns":
            return self._execute_list_campaigns(arguments)
        if function_name == "generate_locations":
            return self._execute_generate_locations(arguments)
        if function_name == "save_locations":
            return self._execute_save_locations(arguments)
        if function_name == "assign_route":
            return self._execute_assign_route(arguments)
        if function_name == "generate_npcs_for_location":
            return self._execute_generate_npcs_for_location(arguments)
        if function_name == "finalize_starting_items":
            return self._execute_finalize_starting_items(arguments)
        if function_name == "update_campaign_phase":
            return self._execute_update_campaign_phase(arguments)

        if function_name != "generate_image":
            return {"success": False, "message": f"Unsupported function: {function_name}"}

        if not self.bot_data.get('image_generation_enabled'):
            return {"success": False, "message": "Image generation disabled for this bot"}

        prompt = arguments.get("prompt", "")
        if not prompt:
            return {"success": False, "message": "No prompt provided"}

        try:
            from shared_utils import generate_image_from_text

            result = generate_image_from_text(prompt)

            if result and result.get("success"):
                image_path = result.get("image_path")
                if image_path and self.send_image_callback:
                    self.send_image_callback(image_path)
                    return {
                        "success": True,
                        "message": f"Image generated: {prompt[:50]}...",
                        "image_path": image_path
                    }
                elif image_path:
                    return {
                        "success": True,
                        "message": f"Image generated at {image_path}",
                        "image_path": image_path
                    }

            return {"success": False, "message": result.get("error", "Image generation failed")}

        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}

