toolbar_html_template = """\
<link rel="stylesheet" type="text/css" href="%(css_path)s">
<style>
#pDocs {
    width: 40px;
    background: #A72D37;
    opacity: 0.8;
    color: white;
    border-left: 1px solid white;
    border-right: 1px solid ##A72D37;
    border-bottom: 1px solid white;
    display: block;
    text-align: center;
    font-size: 10px;
    font-weight: bold;
    padding: 7px 0;
    font-family: serif;
}
#pDocs:hover {
    text-decoration: none;
    opacity: 1.0;
}
</style>
<div id="pDebug">
    <div %(button_style)s id="pDebugToolbarHandle">
        <a title="Show Toolbar" id="pShowToolBarButton"
           href="%(toolbar_url)s" target="pDebugToolbar">&#171;</a>
        <a title="Documentation" id="pDocs" href="/++docs++/">DOC</a>
    </div>
</div>
"""


def monkey_patch_pyramid_debugtoolbar_toolbar_toolbar_html_template():
    import pyramid_debugtoolbar.toolbar

    pyramid_debugtoolbar.toolbar.toolbar_html_template = toolbar_html_template


def includeme(config):
    """Configures access to documentation"""
    settings = config.get_settings()
    registry = config.registry

    monkey_patch_pyramid_debugtoolbar_toolbar_toolbar_html_template()

    if registry["is_debug"]:
        config.add_static_view(
            "++docs++",
            registry["docs_dist"],
            cache_max_age=5
        )
    else:
        config.add_static_view(
            "++docs++",
            registry["docs_dist"],
            permission="view-docs",
            cache_max_age=300,
        )
