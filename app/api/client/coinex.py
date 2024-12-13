import collections
import hashlib
import hmac
import json
import time

import requests


class CoinexApiError(Exception):
    pass


class CoinexClient:
    BASE_URL = "https://api.coinex.com/v2/"

    _headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36",
    }

    def __init__(self, access_id=None, secret=None):
        self._access_id = access_id
        self._secret = secret
        self._log = None

    @property
    def base_url(self):
        return self.BASE_URL

    def add_log(self, log):
        self._log = log

    def _map(self, data, mappings):
        for mapping in mappings:
            data[mapping[1]] = data[mapping[0]]
        return data

    # V2 endpoints - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def market_deals(self, market, **params):
        data, more_pages = self._v2("spot/deals", market=market, **params)
        return data

    def balance_info(self, **params):
        _balances, _ = self._v2("assets/spot/balance", auth=True, **params)
        return {bal.get("ccy"): bal for bal in _balances}

    def order_pending(self, market, page=1, limit=100, **params):
        data, more_pages = self._v2(
            "spot/pending-order", method="get", auth=True, market=market, market_type="SPOT", limit=100, **params
        )
        return data

    def order_limit(self, market, side, amount, price, **params):
        data, _ = self._v2(
            "spot/order",
            method="post",
            auth=True,
            market=market,
            market_type="SPOT",
            side=side,
            type="limit",
            amount=str(amount),
            price=str(price),
            **params,
        )
        return data

    def order_market(self, market, side, amount, **params):
        data, _ = self._v2(
            "spot/order",
            method="post",
            auth=True,
            market=market,
            market_type="SPOT",
            side=side,
            type="market",
            amount=amount,
            **params,
        )
        return data

    def order_user_deals(self, market, page=1, limit=100, start_time=None, **params):
        more_pages = True
        all_data = []
        while more_pages:
            data, more_pages = self._v2(
                "spot/user-deals",
                method="get",
                auth=True,
                market=market,
                market_type="SPOT",
                start_time=start_time,
                limit=1000,
                **params,
            )
            page += 1
            all_data += data
        return all_data

    def order_pending_cancel(self, market, id, **params):
        data, _ = self._v2(
            "spot/cancel-order", method="post", auth=True, market=market, market_type="SPOT", order_id=id, **params
        )
        return data

    def order_status(self, market, id, **params):
        data, _ = self._v2("spot/order-status", method="get", auth=True, market=market, order_id=id, **params)
        return data

    def sub_account_balance(self, sub_user_name=None):
        data, _ = self._v2("account/subs/spot-balance", method="get", auth=True, sub_user_name=sub_user_name)
        return data

    def sub_account_transfer_to_main(self, from_bot, ccy, amount):
        amount = str(amount)
        data, _ = self._v2(
            "account/subs/transfer",
            method="post",
            auth=True,
            from_account_type="SPOT",
            to_account_type="SPOT",
            from_user_name=from_bot,
            ccy=ccy,
            amount=amount,
        )
        return data

    def sub_account_transfer_from_main(self, to_bot, ccy, amount):
        amount = str(amount)
        data, _ = self._v2(
            "account/subs/transfer",
            method="post",
            auth=True,
            from_account_type="SPOT",
            to_account_type="SPOT",
            to_user_name=to_bot,
            ccy=ccy,
            amount=amount,
        )
        return data

    def _process_response(self, resp, path, params):
        resp.raise_for_status()

        data = resp.json()
        if data["code"] != 0:
            raise CoinexApiError(f"error({data['code']})={data['message']} path={path} {params}")

        return data["data"], data.get("pagination", {}).get("has_next")

    def _join_params(self, dictionary):
        if dictionary:
            _data = collections.OrderedDict(sorted(dictionary.items()))
            data_str = "&".join([key + "=" + str(dictionary[key]) for key in sorted(_data)])
            return "?" + data_str
        else:
            return ""

    def _join_body(self, body):
        _body = json.dumps(body)
        return _body

    def _join_pagination(self, page, limit):
        if page and limit:
            return f"&page={page}&limit={limit}"
        elif page:
            return f"&page={page}"
        elif limit:
            return f"&limit={limit}"
        else:
            return ""

    def _sign_v2(self, method="GET", url="", body=None, timestamp=0, page=None, limit=None, **params):
        prepared_string = f"{method}/v2/{url}"
        prepared_string += self._join_params(params)
        if body:
            prepared_string += self._join_body(body)
        prepared_string += self._join_pagination(page, limit)
        prepared_string = f"{prepared_string}{timestamp}"

        signed_str = (
            hmac.new(bytes(self._secret, "latin-1"), msg=bytes(prepared_string, "latin-1"), digestmod=hashlib.sha256)
            .hexdigest()
            .lower()
        )
        return signed_str

    def _v2(self, path, method="get", auth=False, **params):
        request_timeout = int(params.get("timeout", 10000))
        if params.get("timeout"):
            del params["timeout"]

        headers = self._headers
        if auth:
            timestamp = int(time.time() * 1000)
            if method == "post":
                signed = self._sign_v2(method=method.upper(), url=path, timestamp=timestamp, body=params)
            else:
                signed = self._sign_v2(method=method.upper(), url=path, timestamp=timestamp, **params)
            headers = {
                "X-COINEX-KEY": self._access_id,
                "X-COINEX-SIGN": signed,
                "X-COINEX-TIMESTAMP": str(timestamp),
                **headers,
            }

        try:
            if method == "post":
                resp = requests.post(
                    self.base_url + path,
                    json=params,
                    headers=headers,
                    timeout=request_timeout,
                )
            else:
                fn = getattr(requests, method)
                resp = fn(
                    self.base_url + path,
                    params=params,
                    headers=headers,
                    timeout=request_timeout,
                )
        except Exception as exc:
            msg = f"Error coinex_client V2. url={path} params={params} auth={auth} error={exc}"
            if self._log:
                self._log(msg)
            raise CoinexApiError(msg)

        return self._process_response(resp, path, params)
