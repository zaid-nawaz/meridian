from __future__ import annotations

from src.query.service import ask


def main() -> None:

    print("=" * 60)
    print("MERIDIAN QUERY INTERFACE")
    print("=" * 60)

    while True:

        query = input(
            "\nQuestion "
            "(type 'exit' to quit): "
        ).strip()

        if query.lower() in {
            "exit",
            "quit",
        }:
            break

        response = ask(query)

        print("\n" + "-" * 60)

        print("ANSWER:")
        print(response.answer)

        print("\nCITATIONS:")

        if not response.citations:
            print("None")

        else:

            for citation in response.citations:

                print(
                    f"[{citation.citation_id}] "
                    f"{citation.source} "
                    f"({citation.location})"
                )

        print(
            "\nSufficient evidence:",
            response.sufficient_evidence,
        )


if __name__ == "__main__":
    main()