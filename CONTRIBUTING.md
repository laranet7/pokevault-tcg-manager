# Contributing to PokeVault TCG

Thank you for your interest in contributing to **PokeVault TCG**.

PokeVault TCG is a free, open-source and unofficial project created to help users manage personal Pokémon TCG card collections, track inventory, organize collections and estimate reference values.

Contributions are welcome, but the project must remain clean, stable and aligned with its original purpose.

---

## Project status

PokeVault TCG currently includes:

* Authentication.
* User profile.
* User management.
* Collection management.
* Card search by code and name.
* Collection item tracking.
* Collection valuation.
* Price history.
* Dashboard statistics.
* Sakai Vue / PrimeVue based UI.
* FastAPI backend.
* PostgreSQL database.
* Docker Compose support.

The project does **not** currently aim to include:

* Public store.
* Shopping cart.
* Payment processing.

Please open an issue before proposing large features related to store, cart, payments or public marketplace functionality.

---

## How to contribute

1. Fork the repository.
2. Create a new branch from `main`.

```bash
git checkout -b feature/your-feature-name
```

3. Make your changes.
4. Test the project locally.
5. Commit using a clear message.
6. Open a Pull Request against `main`.

Example branch names:

```txt
feature/dashboard-valuation
feature/card-price-history
fix/login-terms-modal
docs/update-readme
```

---

## Pull Request rules

All changes must be submitted through Pull Requests.

Please do not push directly to `main`.

Pull Requests should include:

* A clear description of the change.
* Screenshots if the change affects the UI.
* Notes about backend changes, migrations or new environment variables.
* Steps used to test the change.
* Any known limitations.

Before opening a Pull Request, please make sure:

* The frontend builds correctly.
* The backend starts correctly.
* No `.env` files are committed.
* No API keys, tokens, passwords or credentials are committed.
* Existing authentication and navigation still work.
* Existing collection and card features are not broken.

---

## Code style guidelines

### Frontend

The frontend is based on **Sakai Vue / PrimeVue**.

Please follow these rules:

* Keep the visual style consistent with Sakai.
* Use PrimeVue components when possible.
* Avoid unnecessary custom CSS.
* Do not replace the layout system unless discussed first.
* Keep API calls inside the frontend API layer.
* Keep components focused and reusable.
* Respect the existing light/dark theme behavior.

### Backend

The backend uses **FastAPI**, **SQLAlchemy**, **Alembic** and **PostgreSQL**.

Please follow these rules:

* Keep routers, services, repositories, models and schemas separated.
* Do not put business logic directly inside routers when it can live in services.
* Add Alembic migrations for database changes.
* Validate user access when working with authenticated resources.
* Handle errors clearly.
* Avoid duplicated logic.
* Keep price and valuation logic centralized in backend services.

---

## Security rules

Do not commit:

* `.env` files.
* API keys.
* Database passwords.
* JWT secrets.
* Personal data.
* Real production credentials.
* Generated local database files.
* Private user exports.

Use `.env.example` for documenting required environment variables.

If you find a security issue, please do not open a public issue with exploit details. Open a private report or contact the maintainer directly.

---

## Disclaimer

PokeVault TCG is an unofficial, fan-made and open-source project.

PokeVault TCG is not affiliated with, endorsed, sponsored, supported or approved by Nintendo, Creatures Inc., GAME FREAK inc., The Pokémon Company or The Pokémon Company International.

All names, trademarks, characters, card images and references related to Pokémon belong to their respective owners.

Any use of Pokémon-related names or references in this project is strictly descriptive, informational and intended for personal collection management.

---

## Responsibility

PokeVault TCG is provided as-is.

The maintainers and contributors are not responsible for:

* Data loss.
* Incorrect valuations.
* API errors.
* External service changes.
* Installation issues.
* Commercial decisions made using the application.
* Any direct or indirect damage caused by using, modifying or deploying the project.

Users are responsible for validating, backing up and reviewing their own data.

---

## Support

PokeVault TCG is free and open source.

If you find the project useful and would like to support its development, you can send a voluntary contribution:

[Support PokeVault TCG via PayPal](https://paypal.me/pokevaulttcg)

Contributions are completely optional. PokeVault TCG will remain free and open source.

---

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project.