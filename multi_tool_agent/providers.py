from .config import get_available_providers


def show_available_providers():
    providers = get_available_providers()

    if not providers:
        print("[Provider Manager] No API keys configured.")
        return

    print("[Provider Manager] Available providers:")

    for provider in providers:
        print(f"  ✓ {provider}")


if __name__ == "__main__":
    show_available_providers()