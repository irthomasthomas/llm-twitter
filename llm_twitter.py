import llm
from typing import Optional
import json
import tweepy
import click
import os

class TwitterProfile:
    """
    Represents a Twitter profile with methods to fetch and cache user data.
    """
    def __init__(self, user_data: dict):
        self.user_data = user_data

    @classmethod
    def from_username(cls, client: tweepy.Client, username: str, force_refresh: bool = False) -> "TwitterProfile":
        """
        Fetches and caches a Twitter profile from a given username.
        """
        username = username.lstrip("@")
        cache_file = f"twitter_profile_{username}.json"

        if not force_refresh:
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                click.echo(f"Using cached profile for @{username}")
                return cls(data)
            except FileNotFoundError:
                pass

        user = client.get_user(username=username, user_fields=["description", "public_metrics"])
        if not user.data:
            raise ValueError(f"Could not fetch profile for @{username}")

        data = {
            "username": user.data.username,
            "name": user.data.name,
            "description": user.data.description,
            "followers_count": user.data.public_metrics["followers_count"],
            "following_count": user.data.public_metrics["following_count"],
            "tweet_count": user.data.public_metrics["tweet_count"],
        }

        with open(cache_file, "w") as f:
            json.dump(data, f)

        click.echo(f"Fetched and cached profile for @{username}")
        return cls(data)

    def to_markdown(self) -> str:
        """
        Converts the Twitter profile data to a Markdown formatted string.
        """
        return (
            f"# @{self.user_data['username']}\n"
            f"**Name:** {self.user_data['name']}\n"
            f"**Description:** {self.user_data['description']}\n"
            f"**Followers:** {self.user_data['followers_count']}\n"
            f"**Following:** {self.user_data['following_count']}\n"
            f"**Tweets:** {self.user_data['tweet_count']}\n"
        )

@llm.hookimpl
def register_commands(cli):
    @cli.command()
    @click.argument("prompt")
    @click.option(
        "-a",
        "--account",
        help="Twitter account (username or @username)",
        required=True,
    )
    @click.option(
        "--no-stream",
        is_flag=True,
        help="Do not stream output",
    )
    @click.option(
        "-f",
        "--force-refresh",
        is_flag=True,
        help="Force refresh of the cached profile",
    )
    @click.option(
        "-m",
        "--model",
        help="Model to use for the response",
    )
    def twitter(prompt: str, account: str, no_stream: bool, force_refresh: bool, model: Optional[str]):
        """
        Answer questions about a Twitter account, optionally using a cached profile.
        """
        bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
        if not bearer_token:
            raise click.ClickException("TWITTER_BEARER_TOKEN environment variable is not set")

        client = tweepy.Client(bearer_token=bearer_token)
        
        try:
            profile = TwitterProfile.from_username(client, account, force_refresh)
        except ValueError as e:
            raise click.ClickException(str(e))

        system_prompt = (
            "You are a helpful assistant that answers questions based on a user's Twitter profile."
        )

        combined_prompt = f"{system_prompt}\n\n{profile.to_markdown()}\n\nQuestion: {prompt}"
        model_name = model if model else llm.get_default_model()
        model = llm.get_model(model_name)

        if no_stream:
            response = model.prompt(combined_prompt)
            click.echo(response.text())
        else:
            response = model.prompt(combined_prompt, stream=True)
            for chunk in response:
                click.echo(chunk, nl=False)

@llm.hookimpl
def register_models(register):
    pass

@llm.hookimpl
def register_prompts(register):
    pass