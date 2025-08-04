import cloup

from edenredtools.cli.commands import Oauth2LocalProxyCommand

ENVVAR_PREFIX = "EDENRED_TOOLS"

CLI_SETTINGS = cloup.Context.settings(
    align_option_groups=True,
    align_sections=True,
    show_constraints=True,
    show_subcommand_aliases=True,
    auto_envvar_prefix=ENVVAR_PREFIX,
    formatter_settings=cloup.HelpFormatter.settings(
        max_width=100,
        col1_max_width=40,
        col2_min_width=60,
        indent_increment=3,
        col_spacing=3,
        theme=cloup.HelpTheme(
            invoked_command=cloup.Style(fg='bright_yellow'),
            heading=cloup.Style(fg='bright_white', bold=True),
            constraint=cloup.Style(fg='magenta'),
            col1=cloup.Style(fg='bright_yellow')
        )
    )
)


@cloup.group(help="Edenred developer utilities CLI.")
@cloup.pass_context
def edenred_tools(ctx: cloup.Context) -> None:
    pass


@edenred_tools.group("oauth2", help="Commands related to OAuth2 flows and utilities.")
@cloup.pass_context
def edenred_tools_oauth2(ctx: cloup.Context) -> None:
    pass


@edenred_tools_oauth2.command(
    "local-proxy",
    help="Start a local OAuth2 redirect proxy that listens for authorization callbacks."
)
@cloup.pass_context
@cloup.option(
    "-url", "--callback-url", "callback_url",
    type=str,
    required=True,
    help="The redirect URI (e.g. 'http://localhost:8080/oauth/callback')."
)
@cloup.option(
    "-port", "--proxy-port", "proxy_port",
    type=int,
    default=8888,
    show_default=True,
    help="Local port on which the proxy server should listen for incoming redirect callbacks."
)
@cloup.option(
    "-timeout", "--authorize-timeout", "authorize_flow_timeout",
    type=int,
    default=60,
    show_default=True,
    help="Maximum time (in seconds) to wait for the OAuth2 authorization flow to complete."
)
@cloup.option(
    "-autoconf", "--autoconfigure-system", "autoconfigure_system",
    type=bool,
    default=False,
    show_default=True,
    help="If true, maps the callback hostname to 127.0.0.1 using the local DNS resolver (/etc/hosts or equivalent)."
)
def edenred_tools_oauth2_local_proxy(
    ctx: cloup.Context,
    callback_url: str,
    proxy_port: int,
    authorize_flow_timeout: int,
    autoconfigure_system: bool
) -> None:
    """
    Launch a local OAuth2 authorization proxy server that intercepts browser
    redirects and captures tokens for CLI or development use.
    """
    Oauth2LocalProxyCommand(
        callback_url=callback_url,
        proxy_port=proxy_port,
        authorize_flow_timeout=authorize_flow_timeout,
        autoconfigure_system=autoconfigure_system
    ).execute()


def run() -> None:
    try:
        edenred_tools()
    except Exception as e:
        raise e