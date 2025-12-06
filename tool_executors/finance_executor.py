"""
Finance tool executor mixin for Signal bots.

Contains stock quote, news, search, and financial data tool methods.
"""

import logging

logger = logging.getLogger(__name__)


class FinanceToolsMixin:
    """Mixin providing finance tool execution methods."""

    def _execute_stock_quote(self, arguments: dict) -> dict:
        """Execute the get_stock_quote tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_ticker_info_sync

            result = get_ticker_info_sync(symbol)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Stock quote retrieved for {result.get('symbol', symbol)}"
            }

        except Exception as e:
            logger.error(f"Error getting stock quote: {e}")
            return {"success": False, "message": f"Error getting stock quote: {str(e)}"}

    def _execute_stock_news(self, arguments: dict) -> dict:
        """Execute the get_stock_news tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        count = arguments.get("count", 5)

        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_ticker_news_sync

            result = get_ticker_news_sync(symbol, count)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved {result.get('count', 0)} news articles for {symbol}"
            }

        except Exception as e:
            logger.error(f"Error getting stock news: {e}")
            return {"success": False, "message": f"Error getting stock news: {str(e)}"}

    def _execute_search_stocks(self, arguments: dict) -> dict:
        """Execute the search_stocks tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        query = arguments.get("query", "")
        count = arguments.get("count", 10)

        if not query:
            return {"success": False, "message": "Search query is required"}

        try:
            from signal_bot.finance_client import search_symbols_sync

            result = search_symbols_sync(query, count)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Found {result.get('count', 0)} results for '{query}'"
            }

        except Exception as e:
            logger.error(f"Error searching stocks: {e}")
            return {"success": False, "message": f"Error searching stocks: {str(e)}"}

    def _execute_top_stocks(self, arguments: dict) -> dict:
        """Execute the get_top_stocks tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        entity_type = arguments.get("entity_type", "companies")
        sector = arguments.get("sector", "technology")
        count = arguments.get("count", 10)

        try:
            from signal_bot.finance_client import get_top_entities_sync

            result = get_top_entities_sync(entity_type, sector, count)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved top {entity_type} in {sector} sector"
            }

        except Exception as e:
            logger.error(f"Error getting top stocks: {e}")
            return {"success": False, "message": f"Error getting top stocks: {str(e)}"}

    def _execute_price_history(self, arguments: dict) -> dict:
        """Execute the get_price_history tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        period = arguments.get("period", "1mo")
        interval = arguments.get("interval", "1d")

        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_price_history_sync

            result = get_price_history_sync(symbol, period, interval)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved {result.get('data_points', 0)} data points for {symbol}"
            }

        except Exception as e:
            logger.error(f"Error getting price history: {e}")
            return {"success": False, "message": f"Error getting price history: {str(e)}"}

    def _execute_options(self, arguments: dict) -> dict:
        """Execute the get_options tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        option_type = arguments.get("option_type", "both")
        date = arguments.get("date")

        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_option_chain_sync

            result = get_option_chain_sync(symbol, option_type, date)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved options chain for {symbol} expiring {result.get('expiration_date', 'N/A')}"
            }

        except Exception as e:
            logger.error(f"Error getting options: {e}")
            return {"success": False, "message": f"Error getting options: {str(e)}"}

    def _execute_earnings(self, arguments: dict) -> dict:
        """Execute the get_earnings tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        period = arguments.get("period", "quarterly")

        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_earnings_sync

            result = get_earnings_sync(symbol, period)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved {period} earnings data for {result.get('name', symbol)}"
            }

        except Exception as e:
            logger.error(f"Error getting earnings: {e}")
            return {"success": False, "message": f"Error getting earnings: {str(e)}"}

    def _execute_analyst_ratings(self, arguments: dict) -> dict:
        """Execute the get_analyst_ratings tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_analyst_ratings_sync

            result = get_analyst_ratings_sync(symbol)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved analyst ratings for {result.get('name', symbol)}"
            }

        except Exception as e:
            logger.error(f"Error getting analyst ratings: {e}")
            return {"success": False, "message": f"Error getting analyst ratings: {str(e)}"}

    def _execute_dividends(self, arguments: dict) -> dict:
        """Execute the get_dividends tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        include_history = arguments.get("include_history", False)

        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_dividends_sync

            result = get_dividends_sync(symbol, include_history)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved dividend data for {result.get('name', symbol)}"
            }

        except Exception as e:
            logger.error(f"Error getting dividends: {e}")
            return {"success": False, "message": f"Error getting dividends: {str(e)}"}

    def _execute_financials(self, arguments: dict) -> dict:
        """Execute the get_financials tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        period = arguments.get("period", "annual")

        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_financials_sync

            result = get_financials_sync(symbol, period)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved {period} financials for {result.get('name', symbol)}"
            }

        except Exception as e:
            logger.error(f"Error getting financials: {e}")
            return {"success": False, "message": f"Error getting financials: {str(e)}"}

    def _execute_holders(self, arguments: dict) -> dict:
        """Execute the get_holders tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_holders_sync

            result = get_holders_sync(symbol)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved holder data for {result.get('name', symbol)}"
            }

        except Exception as e:
            logger.error(f"Error getting holders: {e}")
            return {"success": False, "message": f"Error getting holders: {str(e)}"}

    # Reaction tool execution method

