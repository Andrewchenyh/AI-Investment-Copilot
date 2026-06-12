from evals.store_results import list_eval_runs


def main() -> None:
    runs = list_eval_runs()

    if not runs:
        print("No eval runs found.")
        return

    for run in runs:
        print(
            f"#{run['id']} | {run['created_at']} | "
            f"{run['passed']}/{run['total']} passed | "
            f"pass_rate={run['pass_rate']:.1%}"
        )


if __name__ == "__main__":
    main()