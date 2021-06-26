"""
Minimum age (days listed) pair list filter
"""
import logging
from typing import Any, Dict, List, Optional

from pandas import DataFrame

from freqtrade.exceptions import OperationalException
from freqtrade.plugins.pairlist.IPairList import IPairList

logger = logging.getLogger(__name__)


class CurrencyFilter(IPairList):

    # Checked symbols cache (dictionary of ticker symbol => timestamp)
    _symbolsChecked: Dict[str, int] = {}

    def __init__(self, exchange, pairlistmanager,
                 config: Dict[str, Any], pairlistconfig: Dict[str, Any],
                 pairlist_pos: int) -> None:
        super().__init__(exchange, pairlistmanager, config, pairlistconfig, pairlist_pos)

        self._available_currencies = pairlistconfig.get('available_currencies',
                                                        config.get('stake_currency'))

        if len(self._available_currencies) < 1:
            raise OperationalException("CurrencyFilter requires at lease one stake currency")

    @property
    def needstickers(self) -> bool:
        """
        Boolean property defining if tickers are necessary.
        If no Pairlist requires tickers, an empty Dict is passed
        as tickers argument to filter_pairlist
        """
        return False

    def short_desc(self) -> str:
        """
        Short whitelist method description - used for startup-messages
        """
        return (f"{self.name} - Filtering pairs that don't have {self._available_currencies} available.")

    def filter_pairlist(self, pairlist: List[str], tickers: Dict) -> List[str]:
        """
        :param pairlist: pairlist to filter or sort
        :param tickers: Tickers (from exchange.get_tickers()). May be cached.
        :return: new allowlist
        """
        needed_pairs = [(p, '1d') for p in pairlist if p not in self._symbolsChecked]
        if not needed_pairs:
            return pairlist

        markets = self._exchange.markets
        if not markets:
            raise OperationalException(
                'Markets not loaded. Make sure that exchange is initialized correctly.')

        for pair in pairlist:
            for currency in self._available_currencies:
                if f"{pair.split('/')[0]}/{currency}" not in markets:
                    pairlist.remove(pair)
                    break

        self.log_once(f"Validated {len(pairlist)} pairs.", logger.info)
        return pairlist

    def _validate_pair_loc(self, pair: str, daily_candles: Optional[DataFrame]) -> bool:
        """
        Validate age for the ticker
        :param pair: Pair that's currently validated
        :param ticker: ticker dict as returned from ccxt.fetch_tickers()
        :return: True if the pair can stay, false if it should be removed
        """

        markets = self._exchange.markets
        if not markets:
            raise OperationalException(
                'Markets not loaded. Make sure that exchange is initialized correctly.')

        # Check symbol in cache
        if pair in self._symbolsChecked:
            return True

        for currency in self._available_currencies:
            if f"{pair.split('/')[0]}/{currency}" not in markets:
                self.log_once(f"Removed {pair} from whitelist, because "
                              f"{pair.split('/')[0]}/{currency} is does not exists", logger.info)
                return False

        return True
