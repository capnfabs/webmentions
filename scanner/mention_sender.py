import requests


def send_webmention(mention_receiver: str, mentioning_page: str, mentioned_page: str) -> None:
    data = {
        'source': mentioning_page,
        'target': mentioned_page,
    }
    # Pretty sure this is form-encoded by default
    # TODO: timeouts etc
    # TODO: the mention_receiver could be an arbitrary URL, as such:
    #  - check for http/https
    #  - ensure that DNS resolution is only public internet
    #  - verify that resolved IPs are public-internet and not local IPs (can you do this with something like https://stackoverflow.com/questions/53556884/python-cannot-bind-requests-to-network-interface?)
    # - https://docs.gitlab.com/ee/security/webhooks.html

    r = requests.post(mention_receiver, data=data)
    # according to spec, can return a 202 or 201
    # https://www.w3.org/TR/webmention/#sender-notifies-receiver
    # product idea: could maybe eventually use 201s as 'read receipts'
    assert r.ok
