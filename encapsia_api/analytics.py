import encapsia_api

__all__ = ["analytics_connect"]


def analytics_connect():
    """Return an EncapsiaApi object connected to this encapsia server.

    Only intended to be used from within Encapsia Analytics.

    Typical usage:

        !pip install encapsia_api
        import encapsia_api
        api = encapsia_api.analytics_connect()
        # <prints output explaining what has happened>

        # Then use it with e.g.
        api.whoami()
        # etc


    NB: Because of the way the encapsia token is fetched from the user's current session, make sure
    you have seen the output message before trying to use the returned object!!!

    """
    try:
        # We need the jp_proxy_widget module and JupyterLab plugin installed.
        # They should be present in Encapsia Analytics.
        import jp_proxy_widget
    except ModuleNotFoundError:
        raise RuntimeError(
            "Cannot find jp_proxy_widget module. Are you using a standard Encapsia Analytics environment?"
        )

    # Create the api object now, and then re-initialise in the callback called from the browser code.
    # This allows us to populate it with the settings from the user's own browser environment.
    api = encapsia_api.EncapsiaApi("https://placeholder", "placeholder")

    def receive_url_and_token(url, token):
        api.__init__(url, token)

    p = jp_proxy_widget.JSProxyWidget()
    p.js_init(
        """
        callback(
            window.location.protocol + "//" + window.location.hostname,
            sessionStorage.getItem("token")
        );
        """,
        callback=receive_url_and_token,
    )
    p.element.html(
        "Created connection to local encapsia server from current user's login"
    )

    # The `display` function is a global from IPython.core.display.
    display(p)  # NOQA

    return api
