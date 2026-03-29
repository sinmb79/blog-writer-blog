from bots.blog_config import load_settings


def test_blog_settings_default_to_project_env():
    settings = load_settings()
    assert settings["env_file"].endswith(".env")
    assert settings["project_root"].name == "blog-writer-blog"
