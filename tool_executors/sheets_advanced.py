"""
Google Sheets advanced tool executor mixin for Signal bots.

Contains advanced spreadsheet operations: charts, pivots, protection, groups, slicers, tables.
"""

import logging

logger = logging.getLogger(__name__)


class SheetsAdvancedMixin:
    """Mixin providing advanced Google Sheets tool execution methods."""

    # Type hints for attributes provided by SignalToolExecutorBase
    bot_data: dict
    group_id: str

    # Method provided by SheetsCoreMixin (declared here for type checking)
    def _sheets_enabled(self) -> bool: ...

    def _execute_set_text_format(self, arguments: dict) -> dict:
        """Execute the set_text_format tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}

        try:
            from signal_bot.google_sheets_client import set_text_format_sync

            result = set_text_format_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                bold=arguments.get("bold"),
                italic=arguments.get("italic"),
                underline=arguments.get("underline"),
                strikethrough=arguments.get("strikethrough"),
                font_family=arguments.get("font_family"),
                font_size=arguments.get("font_size")
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Applied text formatting to {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting text format: {e}")
            return {"success": False, "message": f"Error setting text format: {str(e)}"}

    def _execute_set_text_color(self, arguments: dict) -> dict:
        """Execute the set_text_color tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        color = arguments.get("color", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}
        if not color:
            return {"success": False, "message": "color is required (e.g., '#FF0000' or 'red')"}

        try:
            from signal_bot.google_sheets_client import set_text_color_sync

            result = set_text_color_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                color=color
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set text color to {color} on {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting text color: {e}")
            return {"success": False, "message": f"Error setting text color: {str(e)}"}

    def _execute_set_background_color(self, arguments: dict) -> dict:
        """Execute the set_background_color tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        color = arguments.get("color", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}
        if not color:
            return {"success": False, "message": "color is required (e.g., '#FFFF00' or 'yellow')"}

        try:
            from signal_bot.google_sheets_client import set_background_color_sync

            result = set_background_color_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                color=color
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set background color to {color} on {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting background color: {e}")
            return {"success": False, "message": f"Error setting background color: {str(e)}"}

    def _execute_add_hyperlink(self, arguments: dict) -> dict:
        """Execute the add_hyperlink tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        cell = arguments.get("cell", "").strip()
        url = arguments.get("url", "").strip()
        display_text = arguments.get("display_text", "").strip() if arguments.get("display_text") else None

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not cell:
            return {"success": False, "message": "cell is required (e.g., 'A1')"}
        if not url:
            return {"success": False, "message": "url is required"}

        try:
            from signal_bot.google_sheets_client import add_hyperlink_sync

            result = add_hyperlink_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                cell=cell,
                url=url,
                display_text=display_text
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Added hyperlink to {cell}")
            }

        except Exception as e:
            logger.error(f"Error adding hyperlink: {e}")
            return {"success": False, "message": f"Error adding hyperlink: {str(e)}"}

    # Filtering tool execution methods (Batch 2)

    def _execute_set_basic_filter(self, arguments: dict) -> dict:
        """Execute the set_basic_filter tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:E100')"}

        try:
            from signal_bot.google_sheets_client import set_basic_filter_sync

            result = set_basic_filter_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Enabled filter on {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting basic filter: {e}")
            return {"success": False, "message": f"Error setting basic filter: {str(e)}"}

    def _execute_clear_basic_filter(self, arguments: dict) -> dict:
        """Execute the clear_basic_filter tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        sheet_name = arguments.get("sheet_name", "").strip() if arguments.get("sheet_name") else None

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import clear_basic_filter_sync

            result = clear_basic_filter_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Cleared filter")
            }

        except Exception as e:
            logger.error(f"Error clearing basic filter: {e}")
            return {"success": False, "message": f"Error clearing basic filter: {str(e)}"}

    def _execute_create_filter_view(self, arguments: dict) -> dict:
        """Execute the create_filter_view tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        title = arguments.get("title", "").strip()
        range_notation = arguments.get("range", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not title:
            return {"success": False, "message": "title is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:E100')"}

        try:
            from signal_bot.google_sheets_client import create_filter_view_sync

            result = create_filter_view_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                title=title,
                range_notation=range_notation
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Created filter view '{title}'")
            }

        except Exception as e:
            logger.error(f"Error creating filter view: {e}")
            return {"success": False, "message": f"Error creating filter view: {str(e)}"}

    def _execute_delete_filter_view(self, arguments: dict) -> dict:
        """Execute the delete_filter_view tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        filter_view_id = arguments.get("filter_view_id")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if filter_view_id is None:
            return {"success": False, "message": "filter_view_id is required"}

        try:
            from signal_bot.google_sheets_client import delete_filter_view_sync

            result = delete_filter_view_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                filter_view_id=int(filter_view_id)
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted filter view {filter_view_id}")
            }

        except Exception as e:
            logger.error(f"Error deleting filter view: {e}")
            return {"success": False, "message": f"Error deleting filter view: {str(e)}"}

    # Named & protected range tool execution methods (Batch 3)

    def _execute_create_named_range(self, arguments: dict) -> dict:
        """Execute the create_named_range tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        name = arguments.get("name", "").strip()
        range_notation = arguments.get("range", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not name:
            return {"success": False, "message": "name is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A2:A100')"}

        try:
            from signal_bot.google_sheets_client import create_named_range_sync

            result = create_named_range_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                name=name,
                range_notation=range_notation
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Created named range '{name}'")
            }

        except Exception as e:
            logger.error(f"Error creating named range: {e}")
            return {"success": False, "message": f"Error creating named range: {str(e)}"}

    def _execute_delete_named_range(self, arguments: dict) -> dict:
        """Execute the delete_named_range tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        named_range_id = arguments.get("named_range_id", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not named_range_id:
            return {"success": False, "message": "named_range_id is required"}

        try:
            from signal_bot.google_sheets_client import delete_named_range_sync

            result = delete_named_range_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                named_range_id=named_range_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted named range")
            }

        except Exception as e:
            logger.error(f"Error deleting named range: {e}")
            return {"success": False, "message": f"Error deleting named range: {str(e)}"}

    def _execute_list_named_ranges(self, arguments: dict) -> dict:
        """Execute the list_named_ranges tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import list_named_ranges_sync

            result = list_named_ranges_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Listed named ranges")
            }

        except Exception as e:
            logger.error(f"Error listing named ranges: {e}")
            return {"success": False, "message": f"Error listing named ranges: {str(e)}"}

    def _execute_protect_range(self, arguments: dict) -> dict:
        """Execute the protect_range tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        description = arguments.get("description", "").strip() if arguments.get("description") else None
        warning_only = arguments.get("warning_only", False)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}

        try:
            from signal_bot.google_sheets_client import protect_range_sync

            result = protect_range_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                description=description,
                warning_only=warning_only
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Protected {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error protecting range: {e}")
            return {"success": False, "message": f"Error protecting range: {str(e)}"}

    # Find/Replace & Copy/Paste tool execution methods (Batch 4)

    def _execute_find_replace(self, arguments: dict) -> dict:
        """Execute the find_replace tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        find = arguments.get("find", "")
        replacement = arguments.get("replacement", "")
        range_notation = arguments.get("range", "").strip() if arguments.get("range") else None
        match_case = arguments.get("match_case", False)
        match_entire_cell = arguments.get("match_entire_cell", False)
        search_formulas = arguments.get("search_formulas", False)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not find:
            return {"success": False, "message": "find text is required"}

        try:
            from signal_bot.google_sheets_client import find_replace_sync

            result = find_replace_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                find=find,
                replacement=replacement,
                range_notation=range_notation,
                match_case=match_case,
                match_entire_cell=match_entire_cell,
                search_formulas=search_formulas
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Find/replace completed")
            }

        except Exception as e:
            logger.error(f"Error in find/replace: {e}")
            return {"success": False, "message": f"Error in find/replace: {str(e)}"}

    def _execute_copy_paste(self, arguments: dict) -> dict:
        """Execute the copy_paste tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        source_range = arguments.get("source_range", "").strip()
        destination_range = arguments.get("destination_range", "").strip()
        paste_type = arguments.get("paste_type", "all").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not source_range:
            return {"success": False, "message": "source_range is required"}
        if not destination_range:
            return {"success": False, "message": "destination_range is required"}

        try:
            from signal_bot.google_sheets_client import copy_paste_sync

            result = copy_paste_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                source_range=source_range,
                destination_range=destination_range,
                paste_type=paste_type
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Copied {source_range} to {destination_range}")
            }

        except Exception as e:
            logger.error(f"Error in copy/paste: {e}")
            return {"success": False, "message": f"Error in copy/paste: {str(e)}"}

    def _execute_cut_paste(self, arguments: dict) -> dict:
        """Execute the cut_paste tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        source_range = arguments.get("source_range", "").strip()
        destination = arguments.get("destination", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not source_range:
            return {"success": False, "message": "source_range is required"}
        if not destination:
            return {"success": False, "message": "destination is required"}

        try:
            from signal_bot.google_sheets_client import cut_paste_sync

            result = cut_paste_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                source_range=source_range,
                destination=destination
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Moved {source_range} to {destination}")
            }

        except Exception as e:
            logger.error(f"Error in cut/paste: {e}")
            return {"success": False, "message": f"Error in cut/paste: {str(e)}"}

    # Spreadsheet Properties tool execution methods (Batch 8)

    def _execute_set_spreadsheet_timezone(self, arguments: dict) -> dict:
        """Execute the set_spreadsheet_timezone tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        timezone = arguments.get("timezone", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not timezone:
            return {"success": False, "message": "timezone is required"}

        try:
            from signal_bot.google_sheets_client import set_spreadsheet_timezone_sync

            result = set_spreadsheet_timezone_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                timezone=timezone
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Timezone set to {timezone}")
            }

        except Exception as e:
            logger.error(f"Error setting timezone: {e}")
            return {"success": False, "message": f"Error setting timezone: {str(e)}"}

    def _execute_set_spreadsheet_locale(self, arguments: dict) -> dict:
        """Execute the set_spreadsheet_locale tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        locale = arguments.get("locale", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not locale:
            return {"success": False, "message": "locale is required"}

        try:
            from signal_bot.google_sheets_client import set_spreadsheet_locale_sync

            result = set_spreadsheet_locale_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                locale=locale
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Locale set to {locale}")
            }

        except Exception as e:
            logger.error(f"Error setting locale: {e}")
            return {"success": False, "message": f"Error setting locale: {str(e)}"}

    def _execute_set_recalculation_interval(self, arguments: dict) -> dict:
        """Execute the set_recalculation_interval tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        interval = arguments.get("interval", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not interval:
            return {"success": False, "message": "interval is required"}

        valid_intervals = ["on_change", "minute", "hour"]
        if interval.lower() not in valid_intervals:
            return {"success": False, "message": f"Invalid interval. Must be one of: {', '.join(valid_intervals)}"}

        try:
            from signal_bot.google_sheets_client import set_recalculation_interval_sync

            result = set_recalculation_interval_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                interval=interval
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Recalculation interval set to {interval}")
            }

        except Exception as e:
            logger.error(f"Error setting recalculation interval: {e}")
            return {"success": False, "message": f"Error setting recalculation interval: {str(e)}"}

    def _execute_get_spreadsheet_properties(self, arguments: dict) -> dict:
        """Execute the get_spreadsheet_properties tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import get_spreadsheet_properties_sync

            result = get_spreadsheet_properties_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Properties for '{result.get('title', 'spreadsheet')}'"
            }

        except Exception as e:
            logger.error(f"Error getting spreadsheet properties: {e}")
            return {"success": False, "message": f"Error getting properties: {str(e)}"}

    def _execute_set_spreadsheet_theme(self, arguments: dict) -> dict:
        """Execute the set_spreadsheet_theme tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        # Extract optional theme parameters
        primary_font = arguments.get("primary_font")
        text_color = arguments.get("text_color")
        background_color = arguments.get("background_color")
        accent1 = arguments.get("accent1")
        accent2 = arguments.get("accent2")
        accent3 = arguments.get("accent3")
        accent4 = arguments.get("accent4")
        accent5 = arguments.get("accent5")
        accent6 = arguments.get("accent6")
        link_color = arguments.get("link_color")

        # Check at least one parameter is provided
        if not any([primary_font, text_color, background_color, accent1, accent2, accent3, accent4, accent5, accent6, link_color]):
            return {"success": False, "message": "At least one theme property (primary_font or a color) is required"}

        try:
            from signal_bot.google_sheets_client import set_spreadsheet_theme_sync

            result = set_spreadsheet_theme_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                primary_font=primary_font,
                text_color=text_color,
                background_color=background_color,
                accent1=accent1,
                accent2=accent2,
                accent3=accent3,
                accent4=accent4,
                accent5=accent5,
                accent6=accent6,
                link_color=link_color
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Theme updated")
            }

        except Exception as e:
            logger.error(f"Error setting theme: {e}")
            return {"success": False, "message": f"Error setting theme: {str(e)}"}

    # Developer Metadata tool execution methods (Batch 9)

    def _execute_set_developer_metadata(self, arguments: dict) -> dict:
        """Execute the set_developer_metadata tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        key = arguments.get("key", "").strip()
        value = arguments.get("value", "").strip()
        location = arguments.get("location", "spreadsheet").strip().lower()
        sheet_name = arguments.get("sheet_name")
        start_index = arguments.get("start_index")
        end_index = arguments.get("end_index")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not key:
            return {"success": False, "message": "key is required"}
        if not value:
            return {"success": False, "message": "value is required"}

        valid_locations = ["spreadsheet", "sheet", "row", "column"]
        if location not in valid_locations:
            return {"success": False, "message": f"Invalid location. Must be one of: {', '.join(valid_locations)}"}

        try:
            from signal_bot.google_sheets_client import set_developer_metadata_sync

            result = set_developer_metadata_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                key=key,
                value=value,
                location=location,
                sheet_name=sheet_name,
                start_index=start_index,
                end_index=end_index
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Metadata '{key}' set")
            }

        except Exception as e:
            logger.error(f"Error setting developer metadata: {e}")
            return {"success": False, "message": f"Error setting metadata: {str(e)}"}

    def _execute_get_developer_metadata(self, arguments: dict) -> dict:
        """Execute the get_developer_metadata tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        key = arguments.get("key")  # Optional

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import get_developer_metadata_sync

            result = get_developer_metadata_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                key=key.strip() if key else None
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Found {result.get('count', 0)} metadata entries")
            }

        except Exception as e:
            logger.error(f"Error getting developer metadata: {e}")
            return {"success": False, "message": f"Error getting metadata: {str(e)}"}

    def _execute_delete_developer_metadata(self, arguments: dict) -> dict:
        """Execute the delete_developer_metadata tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        metadata_id = arguments.get("metadata_id")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if metadata_id is None:
            return {"success": False, "message": "metadata_id is required"}

        try:
            from signal_bot.google_sheets_client import delete_developer_metadata_sync

            result = delete_developer_metadata_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                metadata_id=int(metadata_id)
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted metadata {metadata_id}")
            }

        except Exception as e:
            logger.error(f"Error deleting developer metadata: {e}")
            return {"success": False, "message": f"Error deleting metadata: {str(e)}"}

    # Member memory tool execution methods

    def _execute_save_member_memory(self, arguments: dict) -> dict:
        """Execute the save_member_memory tool call."""
        if not self.bot_data.get('member_memory_tools_enabled'):
            return {"success": False, "message": "Member memory tools disabled for this bot"}

        member_name = arguments.get("member_name", "").strip()
        slot_type = arguments.get("slot_type", "")
        content = arguments.get("content", "").strip()

        if not member_name:
            return {"success": False, "message": "member_name is required"}
        if not slot_type:
            return {"success": False, "message": "slot_type is required"}
        if not content:
            return {"success": False, "message": "content is required"}

        # Validate slot_type
        valid_slots = ["home_location", "work_info", "interests", "media_prefs", "life_events", "response_prefs", "social_notes"]
        if slot_type not in valid_slots:
            return {"success": False, "message": f"Invalid slot_type. Must be one of: {', '.join(valid_slots)}"}

        try:
            from signal_bot.models import GroupMemberMemory, MessageLog, db
            from datetime import datetime

            # Try to find member_id from message logs
            msg = MessageLog.query.filter_by(
                group_id=self.group_id,
                sender_name=member_name,
                is_bot=False
            ).order_by(MessageLog.timestamp.desc()).first()

            if not msg:
                # Try case-insensitive search
                msg = MessageLog.query.filter(
                    MessageLog.group_id == self.group_id,
                    MessageLog.sender_name.ilike(member_name),
                    MessageLog.is_bot == False
                ).order_by(MessageLog.timestamp.desc()).first()

            if not msg:
                return {
                    "success": False,
                    "message": f"No known member '{member_name}' found in this group's chat history"
                }

            member_id = msg.sender_id
            canonical_name = msg.sender_name  # Use the name as it appears in logs

            # Check if memory already exists for this slot
            # First try by member_id (most accurate)
            existing = None
            if member_id:
                existing = GroupMemberMemory.query.filter_by(
                    group_id=self.group_id,
                    member_id=member_id,
                    slot_type=slot_type
                ).first()

            # Also check by member_name to prevent duplicates from different member_ids
            if not existing:
                existing = GroupMemberMemory.query.filter_by(
                    group_id=self.group_id,
                    member_name=canonical_name,
                    slot_type=slot_type
                ).first()

            if existing:
                # Update existing
                existing.content = content
                existing.member_name = canonical_name
                # Also update member_id if we have a better one
                if member_id and (not existing.member_id or existing.member_id != member_id):
                    existing.member_id = member_id
                existing.updated_at = datetime.utcnow()
                action = "Updated"
            else:
                # Create new
                new_memory = GroupMemberMemory(
                    group_id=self.group_id,
                    member_id=member_id,
                    member_name=canonical_name,
                    slot_type=slot_type,
                    content=content
                )
                db.session.add(new_memory)
                action = "Saved"

            db.session.commit()

            logger.info(f"Member memory {action.lower()}: {canonical_name} ({slot_type}): {content[:50]}...")

            return {
                "success": True,
                "data": {
                    "member_name": canonical_name,
                    "slot_type": slot_type,
                    "content": content,
                    "action": action.lower()
                },
                "message": f"{action} memory for {canonical_name}: {slot_type} = {content[:100]}"
            }

        except Exception as e:
            logger.error(f"Error saving member memory: {e}")
            return {"success": False, "message": f"Error saving memory: {str(e)}"}

    def _execute_get_member_memories(self, arguments: dict) -> dict:
        """Execute the get_member_memories tool call."""
        if not self.bot_data.get('member_memory_tools_enabled'):
            return {"success": False, "message": "Member memory tools disabled for this bot"}

        member_name = arguments.get("member_name", "").strip()

        if not member_name:
            return {"success": False, "message": "member_name is required"}

        try:
            from signal_bot.models import GroupMemberMemory, MessageLog

            # Try to find member_id from message logs
            msg = MessageLog.query.filter_by(
                group_id=self.group_id,
                sender_name=member_name,
                is_bot=False
            ).order_by(MessageLog.timestamp.desc()).first()

            if not msg:
                # Try case-insensitive search
                msg = MessageLog.query.filter(
                    MessageLog.group_id == self.group_id,
                    MessageLog.sender_name.ilike(member_name),
                    MessageLog.is_bot == False
                ).order_by(MessageLog.timestamp.desc()).first()

            # If member found in MessageLog, use their member_id and canonical name
            if msg:
                member_id = msg.sender_id
                canonical_name = msg.sender_name

                # Get memories from BOTH member_id AND member_name (some may be stored differently)
                # Use a dict to deduplicate by slot_type (later entries overwrite earlier)
                memories_by_slot = {}

                # First, get by member_id
                if member_id:
                    for mem in GroupMemberMemory.query.filter_by(
                        group_id=self.group_id,
                        member_id=member_id
                    ).all():
                        memories_by_slot[mem.slot_type] = mem

                # Also get by member_name (may have additional memories stored without member_id)
                for mem in GroupMemberMemory.query.filter_by(
                    group_id=self.group_id,
                    member_name=canonical_name
                ).all():
                    # Only add if not already found by member_id (avoid duplicates)
                    if mem.slot_type not in memories_by_slot:
                        memories_by_slot[mem.slot_type] = mem

                memories = list(memories_by_slot.values())
            else:
                # Member not in MessageLog - search GroupMemberMemory directly by name
                # This handles members who have memories but no recent messages in context
                canonical_name = member_name
                memories = GroupMemberMemory.query.filter_by(
                    group_id=self.group_id,
                    member_name=member_name
                ).all()

                # Try case-insensitive search if exact match fails
                if not memories:
                    memories = GroupMemberMemory.query.filter(
                        GroupMemberMemory.group_id == self.group_id,
                        GroupMemberMemory.member_name.ilike(member_name)
                    ).all()
                    # Update canonical_name if we found memories
                    if memories:
                        canonical_name = memories[0].member_name

            if not memories:
                return {
                    "success": True,
                    "data": {
                        "member_name": canonical_name,
                        "memories": {},
                        "count": 0
                    },
                    "message": f"No saved memories for {canonical_name}"
                }

            memory_dict = {}
            for mem in memories:
                memory_dict[mem.slot_type] = {
                    "content": mem.content,
                    "updated_at": mem.updated_at.isoformat() if mem.updated_at else None
                }

            return {
                "success": True,
                "data": {
                    "member_name": canonical_name,
                    "memories": memory_dict,
                    "count": len(memories)
                },
                "message": f"Found {len(memories)} memories for {canonical_name}"
            }

        except Exception as e:
            logger.error(f"Error getting member memories: {e}")
            return {"success": False, "message": f"Error getting memories: {str(e)}"}

    def _execute_delete_member_memory(self, arguments: dict) -> dict:
        """Execute the delete_member_memory tool call."""
        if not self.bot_data.get('member_memory_tools_enabled'):
            return {"success": False, "message": "Member memory tools disabled for this bot"}

        member_name = arguments.get("member_name", "").strip()
        slot_type = arguments.get("slot_type", "")

        if not member_name:
            return {"success": False, "message": "member_name is required"}
        if not slot_type:
            return {"success": False, "message": "slot_type is required"}

        # Validate slot_type
        valid_slots = ["home_location", "work_info", "interests", "media_prefs", "life_events", "response_prefs", "social_notes", "all"]
        if slot_type not in valid_slots:
            return {"success": False, "message": f"Invalid slot_type. Must be one of: {', '.join(valid_slots)}"}

        try:
            from signal_bot.models import GroupMemberMemory, MessageLog, db

            # Try to find member_id from message logs
            msg = MessageLog.query.filter_by(
                group_id=self.group_id,
                sender_name=member_name,
                is_bot=False
            ).order_by(MessageLog.timestamp.desc()).first()

            if not msg:
                # Try case-insensitive search
                msg = MessageLog.query.filter(
                    MessageLog.group_id == self.group_id,
                    MessageLog.sender_name.ilike(member_name),
                    MessageLog.is_bot == False
                ).order_by(MessageLog.timestamp.desc()).first()

            # If member found in MessageLog, use their member_id and canonical name
            if msg:
                member_id = msg.sender_id
                canonical_name = msg.sender_name
            else:
                # Member not in MessageLog - search GroupMemberMemory directly by name
                member_id = None
                canonical_name = member_name

                # Try to find canonical name from existing memories (case-insensitive)
                existing_mem = GroupMemberMemory.query.filter(
                    GroupMemberMemory.group_id == self.group_id,
                    GroupMemberMemory.member_name.ilike(member_name)
                ).first()
                if existing_mem:
                    canonical_name = existing_mem.member_name

            if slot_type == "all":
                # Delete all memories for this member - try by member_id first
                deleted_count = 0
                if member_id:
                    deleted_count = GroupMemberMemory.query.filter_by(
                        group_id=self.group_id,
                        member_id=member_id
                    ).delete()

                # Fallback: also delete by member_name (handles mismatched member_id or no MessageLog entry)
                if deleted_count == 0:
                    deleted_count = GroupMemberMemory.query.filter_by(
                        group_id=self.group_id,
                        member_name=canonical_name
                    ).delete()

                # Also try case-insensitive if exact match found nothing
                if deleted_count == 0:
                    # Find and delete by case-insensitive match
                    memories_to_delete = GroupMemberMemory.query.filter(
                        GroupMemberMemory.group_id == self.group_id,
                        GroupMemberMemory.member_name.ilike(member_name)
                    ).all()
                    deleted_count = len(memories_to_delete)
                    for mem in memories_to_delete:
                        db.session.delete(mem)

                db.session.commit()

                if deleted_count == 0:
                    return {
                        "success": True,
                        "message": f"No memories found for {canonical_name} to delete"
                    }

                logger.info(f"Deleted all {deleted_count} memories for {canonical_name}")
                return {
                    "success": True,
                    "data": {
                        "member_name": canonical_name,
                        "deleted_count": deleted_count
                    },
                    "message": f"Deleted all {deleted_count} memories for {canonical_name}"
                }
            else:
                # Delete specific slot - try by member_id first
                memory = None
                if member_id:
                    memory = GroupMemberMemory.query.filter_by(
                        group_id=self.group_id,
                        member_id=member_id,
                        slot_type=slot_type
                    ).first()

                # Fallback: search by member_name
                if not memory:
                    memory = GroupMemberMemory.query.filter_by(
                        group_id=self.group_id,
                        member_name=canonical_name,
                        slot_type=slot_type
                    ).first()

                # Case-insensitive fallback
                if not memory:
                    memory = GroupMemberMemory.query.filter(
                        GroupMemberMemory.group_id == self.group_id,
                        GroupMemberMemory.member_name.ilike(member_name),
                        GroupMemberMemory.slot_type == slot_type
                    ).first()

                if not memory:
                    return {
                        "success": True,
                        "message": f"No {slot_type} memory found for {canonical_name}"
                    }

                old_content = memory.content
                db.session.delete(memory)
                db.session.commit()

                logger.info(f"Deleted {slot_type} memory for {canonical_name}: {old_content[:50]}...")
                return {
                    "success": True,
                    "data": {
                        "member_name": canonical_name,
                        "slot_type": slot_type,
                        "deleted_content": old_content
                    },
                    "message": f"Deleted {slot_type} memory for {canonical_name}"
                }

        except Exception as e:
            logger.error(f"Error deleting member memory: {e}")
            return {"success": False, "message": f"Error deleting memory: {str(e)}"}

    def _execute_list_group_members(self, arguments: dict) -> dict:
        """Execute the list_group_members tool call."""
        if not self.bot_data.get('member_memory_tools_enabled'):
            return {"success": False, "message": "Member memory tools disabled for this bot"}

        try:
            from signal_bot.models import GroupMemberMemory, MessageLog
            from sqlalchemy import func

            # Track members we've already processed (by lowercase name for deduplication)
            seen_members = set()
            member_list = []

            # Get distinct non-bot members from message logs
            members = MessageLog.query.filter_by(
                group_id=self.group_id,
                is_bot=False
            ).with_entities(
                MessageLog.sender_id,
                MessageLog.sender_name
            ).distinct().all()

            # Build member list from MessageLog
            for member_id, member_name in members:
                if not member_name:
                    continue

                seen_members.add(member_name.lower())

                # Get memories from BOTH member_id AND member_name (some may be stored differently)
                # Use a set to deduplicate slot_types
                memory_slots = set()

                # First, get by member_id
                if member_id:
                    for (slot_type,) in GroupMemberMemory.query.filter_by(
                        group_id=self.group_id,
                        member_id=member_id
                    ).with_entities(GroupMemberMemory.slot_type).all():
                        memory_slots.add(slot_type)

                # Also get by member_name (may have additional memories stored without member_id)
                for (slot_type,) in GroupMemberMemory.query.filter_by(
                    group_id=self.group_id,
                    member_name=member_name
                ).with_entities(GroupMemberMemory.slot_type).all():
                    memory_slots.add(slot_type)

                member_list.append({
                    "name": member_name,
                    "memory_count": len(memory_slots),
                    "memory_types": list(memory_slots)
                })

            # Also include members who have memories but aren't in MessageLog
            # This handles members who haven't sent recent messages but have stored memories
            memory_only_members = GroupMemberMemory.query.filter_by(
                group_id=self.group_id
            ).with_entities(
                GroupMemberMemory.member_name
            ).distinct().all()

            for (member_name,) in memory_only_members:
                if not member_name or member_name.lower() in seen_members:
                    continue

                seen_members.add(member_name.lower())

                # Get memory count and types
                memory_count = GroupMemberMemory.query.filter_by(
                    group_id=self.group_id,
                    member_name=member_name
                ).count()

                memory_types = GroupMemberMemory.query.filter_by(
                    group_id=self.group_id,
                    member_name=member_name
                ).with_entities(GroupMemberMemory.slot_type).all()
                memory_types = [m[0] for m in memory_types]

                member_list.append({
                    "name": member_name,
                    "memory_count": memory_count,
                    "memory_types": memory_types,
                    "memory_only": True  # Flag that this member isn't in recent chat history
                })

            if not member_list:
                return {
                    "success": True,
                    "data": {"members": [], "count": 0},
                    "message": "No members found in chat history or memories"
                }

            # Sort by memory count (most known members first)
            member_list.sort(key=lambda x: x["memory_count"], reverse=True)

            return {
                "success": True,
                "data": {
                    "members": member_list,
                    "count": len(member_list)
                },
                "message": f"Found {len(member_list)} group members"
            }

        except Exception as e:
            logger.error(f"Error listing group members: {e}")
            return {"success": False, "message": f"Error listing members: {str(e)}"}

    # =========================================================================
    # Sheet Properties Extension Tools
    # =========================================================================

    def _execute_hide_sheet(self, arguments: dict) -> dict:
        """Execute the hide_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}

        try:
            from signal_bot.google_sheets_client import hide_sheet_sync

            result = hide_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Sheet '{sheet_name}' is now hidden")
            }

        except Exception as e:
            logger.error(f"Error hiding sheet: {e}")
            return {"success": False, "message": f"Error hiding sheet: {str(e)}"}

    def _execute_show_sheet(self, arguments: dict) -> dict:
        """Execute the show_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}

        try:
            from signal_bot.google_sheets_client import show_sheet_sync

            result = show_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Sheet '{sheet_name}' is now visible")
            }

        except Exception as e:
            logger.error(f"Error showing sheet: {e}")
            return {"success": False, "message": f"Error showing sheet: {str(e)}"}

    def _execute_set_tab_color(self, arguments: dict) -> dict:
        """Execute the set_tab_color tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        color = arguments.get("color", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}
        if not color:
            return {"success": False, "message": "color is required"}

        try:
            from signal_bot.google_sheets_client import set_tab_color_sync

            result = set_tab_color_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                color=color
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set tab color for '{sheet_name}' to {color}")
            }

        except Exception as e:
            logger.error(f"Error setting tab color: {e}")
            return {"success": False, "message": f"Error setting tab color: {str(e)}"}

    def _execute_set_right_to_left(self, arguments: dict) -> dict:
        """Execute the set_right_to_left tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        right_to_left = arguments.get("right_to_left", True)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}

        try:
            from signal_bot.google_sheets_client import set_right_to_left_sync

            result = set_right_to_left_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                right_to_left=right_to_left
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set RTL for '{sheet_name}'")
            }

        except Exception as e:
            logger.error(f"Error setting RTL: {e}")
            return {"success": False, "message": f"Error setting RTL: {str(e)}"}

    def _execute_get_sheet_properties(self, arguments: dict) -> dict:
        """Execute the get_sheet_properties tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name")  # Optional

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import get_sheet_properties_sync

            result = get_sheet_properties_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Sheet properties retrieved")
            }

        except Exception as e:
            logger.error(f"Error getting sheet properties: {e}")
            return {"success": False, "message": f"Error getting sheet properties: {str(e)}"}

    # =========================================================================
    # Protected Ranges Management Tools
    # =========================================================================

    def _execute_list_protected_ranges(self, arguments: dict) -> dict:
        """Execute the list_protected_ranges tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name")  # Optional

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import list_protected_ranges_sync

            result = list_protected_ranges_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Protected ranges retrieved")
            }

        except Exception as e:
            logger.error(f"Error listing protected ranges: {e}")
            return {"success": False, "message": f"Error listing protected ranges: {str(e)}"}

    def _execute_update_protected_range(self, arguments: dict) -> dict:
        """Execute the update_protected_range tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        protected_range_id = arguments.get("protected_range_id")
        description = arguments.get("description")
        warning_only = arguments.get("warning_only")
        editors = arguments.get("editors")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if protected_range_id is None:
            return {"success": False, "message": "protected_range_id is required"}

        try:
            from signal_bot.google_sheets_client import update_protected_range_sync

            result = update_protected_range_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                protected_range_id=protected_range_id,
                description=description,
                warning_only=warning_only,
                editors=editors
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Protected range updated")
            }

        except Exception as e:
            logger.error(f"Error updating protected range: {e}")
            return {"success": False, "message": f"Error updating protected range: {str(e)}"}

    def _execute_delete_protected_range(self, arguments: dict) -> dict:
        """Execute the delete_protected_range tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        protected_range_id = arguments.get("protected_range_id")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if protected_range_id is None:
            return {"success": False, "message": "protected_range_id is required"}

        try:
            from signal_bot.google_sheets_client import delete_protected_range_sync

            result = delete_protected_range_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                protected_range_id=protected_range_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Protection removed")
            }

        except Exception as e:
            logger.error(f"Error deleting protected range: {e}")
            return {"success": False, "message": f"Error deleting protected range: {str(e)}"}

    def _execute_protect_sheet(self, arguments: dict) -> dict:
        """Execute the protect_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        description = arguments.get("description")
        warning_only = arguments.get("warning_only", False)
        editors = arguments.get("editors")
        unprotected_ranges = arguments.get("unprotected_ranges")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}

        try:
            from signal_bot.google_sheets_client import protect_sheet_sync

            result = protect_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                description=description,
                warning_only=warning_only,
                editors=editors,
                unprotected_ranges=unprotected_ranges
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Sheet '{sheet_name}' protected")
            }

        except Exception as e:
            logger.error(f"Error protecting sheet: {e}")
            return {"success": False, "message": f"Error protecting sheet: {str(e)}"}

    # =========================================================================
    # Filter Views Tools
    # =========================================================================

    def _execute_list_filter_views(self, arguments: dict) -> dict:
        """Execute the list_filter_views tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import list_filter_views_sync

            result = list_filter_views_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Filter views retrieved")
            }

        except Exception as e:
            logger.error(f"Error listing filter views: {e}")
            return {"success": False, "message": f"Error listing filter views: {str(e)}"}

    # =========================================================================
    # Dimension Groups (Row/Column Grouping) Tools
    # =========================================================================

    def _execute_create_row_group(self, arguments: dict) -> dict:
        """Execute the create_row_group tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        start_row = arguments.get("start_row")
        end_row = arguments.get("end_row")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}
        if start_row is None or end_row is None:
            return {"success": False, "message": "start_row and end_row are required"}

        try:
            from signal_bot.google_sheets_client import create_row_group_sync

            result = create_row_group_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                start_row=start_row,
                end_row=end_row
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Created row group {start_row}-{end_row}")
            }

        except Exception as e:
            logger.error(f"Error creating row group: {e}")
            return {"success": False, "message": f"Error creating row group: {str(e)}"}

    def _execute_create_column_group(self, arguments: dict) -> dict:
        """Execute the create_column_group tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        start_column = arguments.get("start_column", "")
        end_column = arguments.get("end_column", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}
        if not start_column or not end_column:
            return {"success": False, "message": "start_column and end_column are required"}

        try:
            from signal_bot.google_sheets_client import create_column_group_sync

            result = create_column_group_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                start_column=start_column,
                end_column=end_column
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Created column group {start_column}-{end_column}")
            }

        except Exception as e:
            logger.error(f"Error creating column group: {e}")
            return {"success": False, "message": f"Error creating column group: {str(e)}"}

    def _execute_delete_row_group(self, arguments: dict) -> dict:
        """Execute the delete_row_group tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        start_row = arguments.get("start_row")
        end_row = arguments.get("end_row")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}
        if start_row is None or end_row is None:
            return {"success": False, "message": "start_row and end_row are required"}

        try:
            from signal_bot.google_sheets_client import delete_row_group_sync

            result = delete_row_group_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                start_row=start_row,
                end_row=end_row
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted row group {start_row}-{end_row}")
            }

        except Exception as e:
            logger.error(f"Error deleting row group: {e}")
            return {"success": False, "message": f"Error deleting row group: {str(e)}"}

    def _execute_delete_column_group(self, arguments: dict) -> dict:
        """Execute the delete_column_group tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        start_column = arguments.get("start_column", "")
        end_column = arguments.get("end_column", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}
        if not start_column or not end_column:
            return {"success": False, "message": "start_column and end_column are required"}

        try:
            from signal_bot.google_sheets_client import delete_column_group_sync

            result = delete_column_group_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                start_column=start_column,
                end_column=end_column
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted column group {start_column}-{end_column}")
            }

        except Exception as e:
            logger.error(f"Error deleting column group: {e}")
            return {"success": False, "message": f"Error deleting column group: {str(e)}"}

    def _execute_collapse_expand_group(self, arguments: dict) -> dict:
        """Execute the collapse_expand_group tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        dimension = arguments.get("dimension", "")
        start_index = arguments.get("start_index", "")
        end_index = arguments.get("end_index", "")
        collapsed = arguments.get("collapsed", True)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}
        if not dimension:
            return {"success": False, "message": "dimension is required (ROWS or COLUMNS)"}
        if not start_index or not end_index:
            return {"success": False, "message": "start_index and end_index are required"}

        try:
            from signal_bot.google_sheets_client import update_dimension_group_sync

            # Convert string indices to appropriate types
            if dimension.upper() == "ROWS":
                s_idx = int(start_index)
                e_idx = int(end_index)
            else:
                s_idx = start_index
                e_idx = end_index

            result = update_dimension_group_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                dimension=dimension,
                start_index=s_idx,
                end_index=e_idx,
                collapsed=collapsed
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Group updated")
            }

        except Exception as e:
            logger.error(f"Error updating dimension group: {e}")
            return {"success": False, "message": f"Error updating dimension group: {str(e)}"}

    def _execute_set_group_control_position(self, arguments: dict) -> dict:
        """Execute the set_group_control_position tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        row_control_after = arguments.get("row_control_after")
        column_control_after = arguments.get("column_control_after")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}

        try:
            from signal_bot.google_sheets_client import set_group_control_position_sync

            result = set_group_control_position_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_control_after=row_control_after,
                column_control_after=column_control_after
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Group control position updated")
            }

        except Exception as e:
            logger.error(f"Error setting group control position: {e}")
            return {"success": False, "message": f"Error setting group control position: {str(e)}"}

    # ==================== Slicers ====================

    def _execute_list_slicers(self, arguments: dict) -> dict:
        """Execute the list_slicers tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import list_slicers_sync

            result = list_slicers_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Found {len(result.get('slicers', []))} slicers"
            }

        except Exception as e:
            logger.error(f"Error listing slicers: {e}")
            return {"success": False, "message": f"Error listing slicers: {str(e)}"}

    def _execute_create_slicer(self, arguments: dict) -> dict:
        """Execute the create_slicer tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "Sheet1")
        data_range = arguments.get("data_range", "")
        # Accept schema name 'column_index'
        column_index = arguments.get("column_index")
        title = arguments.get("title")
        # Accept schema names 'anchor_row/anchor_col'
        anchor_row = arguments.get("anchor_row", 0)
        anchor_col = arguments.get("anchor_col", 0)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not data_range:
            return {"success": False, "message": "data_range is required"}
        if column_index is None:
            return {"success": False, "message": "column_index is required"}

        try:
            from signal_bot.google_sheets_client import create_slicer_sync

            result = create_slicer_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                data_range=data_range,
                column_index=column_index,
                title=title,
                anchor_row=anchor_row,
                anchor_col=anchor_col
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Slicer created with ID {result.get('slicer_id')}"
            }

        except Exception as e:
            logger.error(f"Error creating slicer: {e}")
            return {"success": False, "message": f"Error creating slicer: {str(e)}"}

    def _execute_update_slicer(self, arguments: dict) -> dict:
        """Execute the update_slicer tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        slicer_id = arguments.get("slicer_id")
        title = arguments.get("title")
        column_index = arguments.get("column_index")
        apply_to_pivot_tables = arguments.get("apply_to_pivot_tables")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if slicer_id is None:
            return {"success": False, "message": "slicer_id is required"}

        try:
            from signal_bot.google_sheets_client import update_slicer_sync

            result = update_slicer_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                slicer_id=slicer_id,
                title=title,
                column_index=column_index,
                apply_to_pivot_tables=apply_to_pivot_tables
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Slicer {slicer_id} updated"
            }

        except Exception as e:
            logger.error(f"Error updating slicer: {e}")
            return {"success": False, "message": f"Error updating slicer: {str(e)}"}

    def _execute_delete_slicer(self, arguments: dict) -> dict:
        """Execute the delete_slicer tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        slicer_id = arguments.get("slicer_id")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if slicer_id is None:
            return {"success": False, "message": "slicer_id is required"}

        try:
            from signal_bot.google_sheets_client import delete_slicer_sync

            result = delete_slicer_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                slicer_id=slicer_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Slicer {slicer_id} deleted"
            }

        except Exception as e:
            logger.error(f"Error deleting slicer: {e}")
            return {"success": False, "message": f"Error deleting slicer: {str(e)}"}

    # ==================== Tables ====================

    def _execute_list_tables(self, arguments: dict) -> dict:
        """Execute the list_tables tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import list_tables_sync

            result = list_tables_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Found {len(result.get('tables', []))} tables"
            }

        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return {"success": False, "message": f"Error listing tables: {str(e)}"}

    def _execute_create_table(self, arguments: dict) -> dict:
        """Execute the create_table tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "Sheet1")
        # Accept both schema name 'range_notation' and legacy 'range'
        range_notation = arguments.get("range_notation") or arguments.get("range", "")
        table_name = arguments.get("name", "Table1")
        columns = arguments.get("columns", [])

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range_notation is required"}
        if not columns:
            return {"success": False, "message": "columns is required (list of column definitions)"}

        try:
            from signal_bot.google_sheets_client import create_table_sync

            result = create_table_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                range_notation=range_notation,
                name=table_name,
                columns=columns
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Table created with ID {result.get('table_id')}"
            }

        except Exception as e:
            logger.error(f"Error creating table: {e}")
            return {"success": False, "message": f"Error creating table: {str(e)}"}

    def _execute_delete_table(self, arguments: dict) -> dict:
        """Execute the delete_table tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        table_id = arguments.get("table_id", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not table_id:
            return {"success": False, "message": "table_id is required"}

        try:
            from signal_bot.google_sheets_client import delete_table_sync

            result = delete_table_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                table_id=table_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Table {table_id} deleted"
            }

        except Exception as e:
            logger.error(f"Error deleting table: {e}")
            return {"success": False, "message": f"Error deleting table: {str(e)}"}

    def _execute_update_table_column(self, arguments: dict) -> dict:
        """Execute the update_table_column tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        table_id = arguments.get("table_id", "")
        column_index = arguments.get("column_index")
        name = arguments.get("name")
        column_type = arguments.get("column_type")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not table_id:
            return {"success": False, "message": "table_id is required"}
        if column_index is None:
            return {"success": False, "message": "column_index is required"}

        try:
            from signal_bot.google_sheets_client import update_table_column_sync

            result = update_table_column_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                table_id=table_id,
                column_index=column_index,
                column_name=name,
                column_type=column_type
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Column {column_index} updated in table {table_id}"
            }

        except Exception as e:
            logger.error(f"Error updating table column: {e}")
            return {"success": False, "message": f"Error updating table column: {str(e)}"}

    # =========================================================================
    # Google Calendar Tools
    # =========================================================================

