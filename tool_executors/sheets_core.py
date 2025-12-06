"""
Google Sheets core tool executor mixin for Signal bots.

Contains core spreadsheet operations: create, read, write, format, etc.
"""

import logging

logger = logging.getLogger(__name__)


class SheetsCoreMixin:
    """Mixin providing core Google Sheets tool execution methods."""


    def _sheets_enabled(self) -> bool:
        """Check if Google Sheets is enabled and connected."""
        return (
            self.bot_data.get('google_sheets_enabled', False) and
            self.bot_data.get('google_connected', False)
        )

    def _execute_create_spreadsheet(self, arguments: dict) -> dict:
        """Execute the create_spreadsheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        title = arguments.get("title", "")
        description = arguments.get("description", "")

        if not title:
            return {"success": False, "message": "Title is required"}

        try:
            from signal_bot.google_sheets_client import create_spreadsheet_sync

            result = create_spreadsheet_sync(
                bot_data=self.bot_data,
                group_id=self.group_id,
                title=title,
                description=description,
                created_by=self.sender_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Created spreadsheet '{title}'. IMPORTANT - Share this link with the user: {result.get('url', 'URL unavailable')}"
            }

        except Exception as e:
            logger.error(f"Error creating spreadsheet: {e}")
            return {"success": False, "message": f"Error creating spreadsheet: {str(e)}"}

    def _execute_list_spreadsheets(self, arguments: dict) -> dict:
        """Execute the list_spreadsheets tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        try:
            from signal_bot.google_sheets_client import list_spreadsheets_sync

            result = list_spreadsheets_sync(
                bot_data=self.bot_data,
                group_id=self.group_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Found {result.get('count', 0)} spreadsheet(s) for this group"
            }

        except Exception as e:
            logger.error(f"Error listing spreadsheets: {e}")
            return {"success": False, "message": f"Error listing spreadsheets: {str(e)}"}

    def _execute_read_sheet(self, arguments: dict) -> dict:
        """Execute the read_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        range_notation = arguments.get("range", "Sheet1!A1:Z100")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import read_sheet_sync

            result = read_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Read {result.get('row_count', 0)} rows from sheet"
            }

        except Exception as e:
            logger.error(f"Error reading sheet: {e}")
            return {"success": False, "message": f"Error reading sheet: {str(e)}"}

    def _execute_write_to_sheet(self, arguments: dict) -> dict:
        """Execute the write_to_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        range_notation = arguments.get("range", "")
        values = arguments.get("values", [])

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required"}
        if not values:
            return {"success": False, "message": "values are required"}

        try:
            from signal_bot.google_sheets_client import write_sheet_sync

            result = write_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                values=values
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Updated {result.get('updated_cells', 0)} cells"
            }

        except Exception as e:
            logger.error(f"Error writing to sheet: {e}")
            return {"success": False, "message": f"Error writing to sheet: {str(e)}"}

    def _execute_add_row_to_sheet(self, arguments: dict) -> dict:
        """Execute the add_row_to_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        values = arguments.get("values", [])
        include_metadata = arguments.get("include_metadata", True)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not values:
            return {"success": False, "message": "values are required"}

        try:
            from signal_bot.google_sheets_client import append_to_sheet_sync

            result = append_to_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                values=values,
                added_by=self.sender_name,
                include_metadata=include_metadata
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            row_added = result.get("row_added", [])
            return {
                "success": True,
                "data": result,
                "message": f"Added row: {', '.join(str(v) for v in row_added[:5])}{'...' if len(row_added) > 5 else ''}"
            }

        except Exception as e:
            logger.error(f"Error adding row to sheet: {e}")
            return {"success": False, "message": f"Error adding row to sheet: {str(e)}"}

    def _execute_search_sheets(self, arguments: dict) -> dict:
        """Execute the search_sheets tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        query = arguments.get("query", "")

        if not query:
            return {"success": False, "message": "Search query is required"}

        try:
            from signal_bot.google_sheets_client import search_sheets_sync

            result = search_sheets_sync(
                bot_data=self.bot_data,
                group_id=self.group_id,
                query=query
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Found {result.get('count', 0)} spreadsheet(s) matching '{query}'"
            }

        except Exception as e:
            logger.error(f"Error searching sheets: {e}")
            return {"success": False, "message": f"Error searching sheets: {str(e)}"}

    def _execute_format_columns(self, arguments: dict) -> dict:
        """Execute the format_columns tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        columns = arguments.get("columns", "")
        format_type = arguments.get("format_type", "")
        pattern = arguments.get("pattern")  # Optional

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not columns:
            return {"success": False, "message": "columns is required (e.g., 'B' or 'B:E')"}
        if not format_type:
            return {"success": False, "message": "format_type is required"}

        # Validate format_type
        valid_types = ["CURRENCY", "PERCENT", "NUMBER", "DATE", "TEXT"]
        if format_type.upper() not in valid_types:
            return {"success": False, "message": f"Invalid format_type. Must be one of: {', '.join(valid_types)}"}

        try:
            from signal_bot.google_sheets_client import format_columns_sync

            result = format_columns_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                columns=columns,
                format_type=format_type.upper(),
                pattern=pattern
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Formatted columns {columns} as {format_type}")
            }

        except Exception as e:
            logger.error(f"Error formatting columns: {e}")
            return {"success": False, "message": f"Error formatting columns: {str(e)}"}

    def _execute_clear_range(self, arguments: dict) -> dict:
        """Execute the clear_range tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        range_notation = arguments.get("range", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:C10' or 'B:B')"}

        try:
            from signal_bot.google_sheets_client import clear_range_sync

            result = clear_range_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Cleared range {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error clearing range: {e}")
            return {"success": False, "message": f"Error clearing range: {str(e)}"}

    def _execute_delete_rows(self, arguments: dict) -> dict:
        """Execute the delete_rows tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        start_row = arguments.get("start_row")
        end_row = arguments.get("end_row")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if start_row is None:
            return {"success": False, "message": "start_row is required"}
        if start_row < 1:
            return {"success": False, "message": "start_row must be at least 1"}

        try:
            from signal_bot.google_sheets_client import delete_rows_sync

            result = delete_rows_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                start_row=start_row,
                end_row=end_row
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted row(s)")
            }

        except Exception as e:
            logger.error(f"Error deleting rows: {e}")
            return {"success": False, "message": f"Error deleting rows: {str(e)}"}

    def _execute_delete_columns(self, arguments: dict) -> dict:
        """Execute the delete_columns tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        columns = arguments.get("columns", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not columns:
            return {"success": False, "message": "columns is required (e.g., 'C' or 'C:E')"}

        try:
            from signal_bot.google_sheets_client import delete_columns_sync

            result = delete_columns_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                columns=columns
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted column(s) {columns}")
            }

        except Exception as e:
            logger.error(f"Error deleting columns: {e}")
            return {"success": False, "message": f"Error deleting columns: {str(e)}"}

    def _execute_insert_rows(self, arguments: dict) -> dict:
        """Execute the insert_rows tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        row = arguments.get("row")
        count = arguments.get("count", 1)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if row is None:
            return {"success": False, "message": "row is required"}
        if row < 1:
            return {"success": False, "message": "row must be at least 1"}

        try:
            from signal_bot.google_sheets_client import insert_rows_sync

            result = insert_rows_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                start_row=row,
                num_rows=count
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Inserted {count} row(s) at row {row}")
            }

        except Exception as e:
            logger.error(f"Error inserting rows: {e}")
            return {"success": False, "message": f"Error inserting rows: {str(e)}"}

    def _execute_insert_columns(self, arguments: dict) -> dict:
        """Execute the insert_columns tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        column = arguments.get("column", "")
        count = arguments.get("count", 1)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not column:
            return {"success": False, "message": "column is required (e.g., 'C')"}

        try:
            from signal_bot.google_sheets_client import insert_columns_sync

            result = insert_columns_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                column=column,
                num_columns=count
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Inserted {count} column(s) at column {column}")
            }

        except Exception as e:
            logger.error(f"Error inserting columns: {e}")
            return {"success": False, "message": f"Error inserting columns: {str(e)}"}

    def _execute_add_sheet(self, arguments: dict) -> dict:
        """Execute the add_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        title = arguments.get("title", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not title:
            return {"success": False, "message": "title is required"}

        try:
            from signal_bot.google_sheets_client import add_sheet_sync

            result = add_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                title=title
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Added sheet '{title}'")
            }

        except Exception as e:
            logger.error(f"Error adding sheet: {e}")
            return {"success": False, "message": f"Error adding sheet: {str(e)}"}

    def _execute_delete_sheet(self, arguments: dict) -> dict:
        """Execute the delete_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}

        try:
            from signal_bot.google_sheets_client import delete_sheet_sync

            result = delete_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted sheet '{sheet_name}'")
            }

        except Exception as e:
            logger.error(f"Error deleting sheet: {e}")
            return {"success": False, "message": f"Error deleting sheet: {str(e)}"}

    def _execute_rename_sheet(self, arguments: dict) -> dict:
        """Execute the rename_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        old_name = arguments.get("old_name", "")
        new_name = arguments.get("new_name", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not old_name:
            return {"success": False, "message": "old_name is required"}
        if not new_name:
            return {"success": False, "message": "new_name is required"}

        try:
            from signal_bot.google_sheets_client import rename_sheet_sync

            result = rename_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                old_name=old_name,
                new_name=new_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Renamed sheet to '{new_name}'")
            }

        except Exception as e:
            logger.error(f"Error renaming sheet: {e}")
            return {"success": False, "message": f"Error renaming sheet: {str(e)}"}

    def _execute_freeze_rows(self, arguments: dict) -> dict:
        """Execute the freeze_rows tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        num_rows = arguments.get("num_rows")
        sheet_name = arguments.get("sheet_name")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if num_rows is None:
            return {"success": False, "message": "num_rows is required"}

        try:
            from signal_bot.google_sheets_client import freeze_rows_sync

            result = freeze_rows_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                num_rows=num_rows,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Froze {num_rows} row(s)")
            }

        except Exception as e:
            logger.error(f"Error freezing rows: {e}")
            return {"success": False, "message": f"Error freezing rows: {str(e)}"}

    def _execute_freeze_columns(self, arguments: dict) -> dict:
        """Execute the freeze_columns tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        num_columns = arguments.get("num_columns")
        sheet_name = arguments.get("sheet_name")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if num_columns is None:
            return {"success": False, "message": "num_columns is required"}

        try:
            from signal_bot.google_sheets_client import freeze_columns_sync

            result = freeze_columns_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                num_columns=num_columns,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Froze {num_columns} column(s)")
            }

        except Exception as e:
            logger.error(f"Error freezing columns: {e}")
            return {"success": False, "message": f"Error freezing columns: {str(e)}"}

    def _execute_sort_range(self, arguments: dict) -> dict:
        """Execute the sort_range tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        column = arguments.get("column", "")
        ascending = arguments.get("ascending", True)
        has_header = arguments.get("has_header", True)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not column:
            return {"success": False, "message": "column is required (e.g., 'B')"}

        try:
            from signal_bot.google_sheets_client import sort_range_sync

            result = sort_range_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sort_column=column,
                ascending=ascending,
                has_header=has_header
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Sorted by column {column}")
            }

        except Exception as e:
            logger.error(f"Error sorting range: {e}")
            return {"success": False, "message": f"Error sorting range: {str(e)}"}

    def _execute_auto_resize_columns(self, arguments: dict) -> dict:
        """Execute the auto_resize_columns tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        columns = arguments.get("columns")  # Optional

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import auto_resize_columns_sync

            result = auto_resize_columns_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                columns=columns
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Auto-resized columns")
            }

        except Exception as e:
            logger.error(f"Error auto-resizing columns: {e}")
            return {"success": False, "message": f"Error auto-resizing columns: {str(e)}"}

    def _execute_merge_cells(self, arguments: dict) -> dict:
        """Execute the merge_cells tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        range_notation = arguments.get("range", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:C1')"}

        try:
            from signal_bot.google_sheets_client import merge_cells_sync

            result = merge_cells_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Merged cells {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error merging cells: {e}")
            return {"success": False, "message": f"Error merging cells: {str(e)}"}

    def _execute_unmerge_cells(self, arguments: dict) -> dict:
        """Execute the unmerge_cells tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        range_notation = arguments.get("range", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:C1')"}

        try:
            from signal_bot.google_sheets_client import unmerge_cells_sync

            result = unmerge_cells_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Unmerged cells {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error unmerging cells: {e}")
            return {"success": False, "message": f"Error unmerging cells: {str(e)}"}

    # Batch 4: Formatting & Validation tool execution methods

    def _execute_conditional_format(self, arguments: dict) -> dict:
        """Execute the conditional_format tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        rule_type = arguments.get("rule_type", "")
        condition_value = arguments.get("condition_value")
        format_type = arguments.get("format_type", "background")
        color = arguments.get("color", "red")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'B2:B100')"}
        if not rule_type:
            return {"success": False, "message": "rule_type is required (greater_than, less_than, equals, contains, not_empty, is_empty)"}

        try:
            from signal_bot.google_sheets_client import conditional_format_sync

            result = conditional_format_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                rule_type=rule_type,
                condition_value=condition_value,
                format_type=format_type,
                color=color
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Added conditional formatting to {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error adding conditional format: {e}")
            return {"success": False, "message": f"Error adding conditional format: {str(e)}"}

    def _execute_data_validation(self, arguments: dict) -> dict:
        """Execute the data_validation tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        validation_type = arguments.get("validation_type", "")
        values = arguments.get("values")
        min_value = arguments.get("min_value")
        max_value = arguments.get("max_value")
        strict = arguments.get("strict", True)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'C2:C100')"}
        if not validation_type:
            return {"success": False, "message": "validation_type is required (dropdown, number_range, date, checkbox)"}

        try:
            from signal_bot.google_sheets_client import data_validation_sync

            result = data_validation_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                validation_type=validation_type,
                values=values,
                min_value=min_value,
                max_value=max_value,
                strict=strict
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Added {validation_type} validation to {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error adding data validation: {e}")
            return {"success": False, "message": f"Error adding data validation: {str(e)}"}

    def _execute_alternating_colors(self, arguments: dict) -> dict:
        """Execute the alternating_colors tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        header_color = arguments.get("header_color", "blue")
        first_band_color = arguments.get("first_band_color", "white")
        second_band_color = arguments.get("second_band_color", "lightgray")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:E100')"}

        try:
            from signal_bot.google_sheets_client import alternating_colors_sync

            result = alternating_colors_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                header_color=header_color,
                first_band_color=first_band_color,
                second_band_color=second_band_color
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Added alternating colors to {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error adding alternating colors: {e}")
            return {"success": False, "message": f"Error adding alternating colors: {str(e)}"}

    # Batch 5: Cell Enhancements tool execution methods

    def _execute_add_note(self, arguments: dict) -> dict:
        """Execute the add_note tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        cell = arguments.get("cell", "").strip()
        note = arguments.get("note", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not cell:
            return {"success": False, "message": "cell is required (e.g., 'B2')"}

        try:
            from signal_bot.google_sheets_client import add_note_sync

            result = add_note_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                cell=cell,
                note=note
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Added note to cell {cell}")
            }

        except Exception as e:
            logger.error(f"Error adding note: {e}")
            return {"success": False, "message": f"Error adding note: {str(e)}"}

    def _execute_set_borders(self, arguments: dict) -> dict:
        """Execute the set_borders tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        border_style = arguments.get("border_style", "solid")
        color = arguments.get("color", "black")
        sides = arguments.get("sides", "all")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}

        try:
            from signal_bot.google_sheets_client import set_borders_sync

            result = set_borders_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                border_style=border_style,
                color=color,
                sides=sides
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Added borders to {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting borders: {e}")
            return {"success": False, "message": f"Error setting borders: {str(e)}"}

    def _execute_set_alignment(self, arguments: dict) -> dict:
        """Execute the set_alignment tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        horizontal = arguments.get("horizontal")
        vertical = arguments.get("vertical")
        wrap = arguments.get("wrap")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}
        if not horizontal and not vertical and not wrap:
            return {"success": False, "message": "At least one of horizontal, vertical, or wrap must be specified"}

        try:
            from signal_bot.google_sheets_client import set_alignment_sync

            result = set_alignment_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                horizontal=horizontal,
                vertical=vertical,
                wrap=wrap
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set alignment on {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting alignment: {e}")
            return {"success": False, "message": f"Error setting alignment: {str(e)}"}

    # Batch 10: Additional Cell Formatting tool execution methods

    def _execute_set_text_direction(self, arguments: dict) -> dict:
        """Execute the set_text_direction tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        direction = arguments.get("direction", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}
        if not direction:
            return {"success": False, "message": "direction is required (left_to_right or right_to_left)"}

        try:
            from signal_bot.google_sheets_client import set_text_direction_sync

            result = set_text_direction_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                direction=direction
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set text direction to {direction} on {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting text direction: {e}")
            return {"success": False, "message": f"Error setting text direction: {str(e)}"}

    def _execute_set_text_rotation(self, arguments: dict) -> dict:
        """Execute the set_text_rotation tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        angle = arguments.get("angle")
        vertical = arguments.get("vertical")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}
        if angle is None and not vertical:
            return {"success": False, "message": "Either 'angle' or 'vertical' must be specified"}

        try:
            from signal_bot.google_sheets_client import set_text_rotation_sync

            result = set_text_rotation_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                angle=angle,
                vertical=vertical
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            rotation_desc = "vertical" if vertical else f"{angle} degrees"
            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set text rotation to {rotation_desc} on {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting text rotation: {e}")
            return {"success": False, "message": f"Error setting text rotation: {str(e)}"}

    def _execute_set_cell_padding(self, arguments: dict) -> dict:
        """Execute the set_cell_padding tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        top = arguments.get("top")
        right = arguments.get("right")
        bottom = arguments.get("bottom")
        left = arguments.get("left")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}
        if top is None and right is None and bottom is None and left is None:
            return {"success": False, "message": "At least one padding value (top, right, bottom, left) must be specified"}

        try:
            from signal_bot.google_sheets_client import set_cell_padding_sync

            result = set_cell_padding_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                top=top,
                right=right,
                bottom=bottom,
                left=left
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set cell padding on {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting cell padding: {e}")
            return {"success": False, "message": f"Error setting cell padding: {str(e)}"}

    def _execute_set_rich_text(self, arguments: dict) -> dict:
        """Execute the set_rich_text tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        cell = arguments.get("cell", "").strip()
        text = arguments.get("text", "")
        runs = arguments.get("runs", [])

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not cell:
            return {"success": False, "message": "cell is required (e.g., 'A1')"}
        if not text:
            return {"success": False, "message": "text is required"}
        if not runs or len(runs) == 0:
            return {"success": False, "message": "At least one format run is required"}

        try:
            from signal_bot.google_sheets_client import set_rich_text_sync

            result = set_rich_text_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                cell=cell,
                text=text,
                runs=runs
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Applied {len(runs)} format run(s) to {cell}")
            }

        except Exception as e:
            logger.error(f"Error setting rich text: {e}")
            return {"success": False, "message": f"Error setting rich text: {str(e)}"}

    # Batch 6: Charts tool execution methods

    def _execute_create_chart(self, arguments: dict) -> dict:
        """Execute the create_chart tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        data_range = arguments.get("data_range", "").strip()
        chart_type = arguments.get("chart_type", "column")
        title = arguments.get("title", "")
        anchor_cell = arguments.get("anchor_cell", "F1")
        legend_position = arguments.get("legend_position", "bottom")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not data_range:
            return {"success": False, "message": "data_range is required (e.g., 'A1:C10')"}

        try:
            from signal_bot.google_sheets_client import create_chart_sync

            result = create_chart_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                data_range=data_range,
                chart_type=chart_type,
                title=title,
                anchor_cell=anchor_cell,
                legend_position=legend_position
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Created {chart_type} chart")
            }

        except Exception as e:
            logger.error(f"Error creating chart: {e}")
            return {"success": False, "message": f"Error creating chart: {str(e)}"}

    def _execute_list_charts(self, arguments: dict) -> dict:
        """Execute the list_charts tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import list_charts_sync

            result = list_charts_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Listed charts")
            }

        except Exception as e:
            logger.error(f"Error listing charts: {e}")
            return {"success": False, "message": f"Error listing charts: {str(e)}"}

    def _execute_update_chart(self, arguments: dict) -> dict:
        """Execute the update_chart tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        chart_id = arguments.get("chart_id")
        title = arguments.get("title")
        chart_type = arguments.get("chart_type")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if chart_id is None:
            return {"success": False, "message": "chart_id is required (use list_charts to get IDs)"}

        try:
            from signal_bot.google_sheets_client import update_chart_sync

            result = update_chart_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                chart_id=int(chart_id),
                title=title,
                chart_type=chart_type
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Updated chart {chart_id}")
            }

        except Exception as e:
            logger.error(f"Error updating chart: {e}")
            return {"success": False, "message": f"Error updating chart: {str(e)}"}

    def _execute_delete_chart(self, arguments: dict) -> dict:
        """Execute the delete_chart tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        chart_id = arguments.get("chart_id")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if chart_id is None:
            return {"success": False, "message": "chart_id is required (use list_charts to get IDs)"}

        try:
            from signal_bot.google_sheets_client import delete_chart_sync

            result = delete_chart_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                chart_id=int(chart_id)
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted chart {chart_id}")
            }

        except Exception as e:
            logger.error(f"Error deleting chart: {e}")
            return {"success": False, "message": f"Error deleting chart: {str(e)}"}

    # Batch 7: Pivot Tables tool execution methods

    def _execute_create_pivot_table(self, arguments: dict) -> dict:
        """Execute the create_pivot_table tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        source_range = arguments.get("source_range", "").strip()
        row_groups = arguments.get("row_groups")
        values = arguments.get("values")
        anchor_cell = arguments.get("anchor_cell", "F1")
        column_groups = arguments.get("column_groups")
        show_totals = arguments.get("show_totals", True)
        sort_order = arguments.get("sort_order", "ASCENDING")
        value_layout = arguments.get("value_layout", "HORIZONTAL")
        filter_specs = arguments.get("filter_specs")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not source_range:
            return {"success": False, "message": "source_range is required (e.g., 'A1:D100')"}
        if not row_groups or not isinstance(row_groups, list):
            return {"success": False, "message": "row_groups is required (array of group definitions with 'column' and optional 'date_group_rule', 'histogram_rule')"}
        if not values or not isinstance(values, list):
            return {"success": False, "message": "values is required (array of value definitions with 'column' and optional 'function', 'name')"}

        try:
            from signal_bot.google_sheets_client import create_pivot_table_sync

            result = create_pivot_table_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                source_range=source_range,
                row_groups=row_groups,
                values=values,
                anchor_cell=anchor_cell,
                column_groups=column_groups,
                show_totals=show_totals,
                sort_order=sort_order,
                value_layout=value_layout,
                filter_specs=filter_specs
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Created pivot table")
            }

        except Exception as e:
            logger.error(f"Error creating pivot table: {e}")
            return {"success": False, "message": f"Error creating pivot table: {str(e)}"}

    def _execute_delete_pivot_table(self, arguments: dict) -> dict:
        """Execute the delete_pivot_table tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        anchor_cell = arguments.get("anchor_cell", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not anchor_cell:
            return {"success": False, "message": "anchor_cell is required (e.g., 'F1')"}

        try:
            from signal_bot.google_sheets_client import delete_pivot_table_sync

            result = delete_pivot_table_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                anchor_cell=anchor_cell
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted pivot table at {anchor_cell}")
            }

        except Exception as e:
            logger.error(f"Error deleting pivot table: {e}")
            return {"success": False, "message": f"Error deleting pivot table: {str(e)}"}

    def _execute_list_pivot_tables(self, arguments: dict) -> dict:
        """Execute the list_pivot_tables tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import list_pivot_tables_sync

            result = list_pivot_tables_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Listed pivot tables")
            }

        except Exception as e:
            logger.error(f"Error listing pivot tables: {e}")
            return {"success": False, "message": f"Error listing pivot tables: {str(e)}"}

    def _execute_get_pivot_table(self, arguments: dict) -> dict:
        """Execute the get_pivot_table tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        anchor_cell = arguments.get("anchor_cell", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not anchor_cell:
            return {"success": False, "message": "anchor_cell is required (e.g., 'F1')"}

        try:
            from signal_bot.google_sheets_client import get_pivot_table_sync

            result = get_pivot_table_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                anchor_cell=anchor_cell
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Got pivot table at {anchor_cell}")
            }

        except Exception as e:
            logger.error(f"Error getting pivot table: {e}")
            return {"success": False, "message": f"Error getting pivot table: {str(e)}"}

    # Text formatting & color tool execution methods (Batch 1)

