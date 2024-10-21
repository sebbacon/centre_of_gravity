This app was mostly made by talking with Anthropic's Claude using my voice while walking to the office. This README is therefore a bit random, as it was generated during that walk.

Here's how it works:

Get a Google Maps API Key (see below).

Get people.js, our canonical source of locations:

    curl -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
               -H "Accept: application/vnd.github.v3.raw" \
               -o people.js \
               https://raw.githubusercontent.com/ebmdatalab/team-manual/refs/heads/main/team-map/people.js

See if our version of it in this repo (locations_config.json) needs updating:

    python src/cli.py update-locations --source-file people.js

Update travel time data (uses Google Maps API):

    python src/cli.py update-routes

Build a single-page app that uses this data:

    python src/cli.py build-html

All the above steps are supposedly exercised by the build-and-release.yml Github Workflow, so in theory this could run standalong (but it needs a PAT or similar for the `curl` step to work).

The idea is that an extra step would be added to the end of the workflow to upload the resulting HTML page to the team manual.

# UV Setup, Project Dependencies, GitHub CI Guide, and Google Maps API Setup

[Previous content remains unchanged]

## Obtaining a Google Maps API Key

To use the Google Maps services in this project, you need to obtain an API key from Google. Follow these steps:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).

2. Create a new project or select an existing one.

3. Enable the necessary APIs:

   - In the sidebar, click on "APIs & Services" > "Library".
   - Search for and enable the following APIs:
     - Directions API
     - Distance Matrix API
     - Geocoding API

4. Create credentials:

   - In the sidebar, click on "APIs & Services" > "Credentials".
   - Click the "Create Credentials" button and select "API key".

5. Restrict your API key:

   - After creating the key, click on "Edit API key".
   - Under "Application restrictions", choose "HTTP referrers" and add your allowed domains.
   - Under "API restrictions", select "Restrict key" and choose the APIs you enabled in step 3.

6. Copy your API key.

### Using Your API Key

1. For local development:

   - Create a `.env` file in your project root if you haven't already.
   - Add your API key to the `.env` file:
     ```
     GOOGLE_MAPS_API_KEY=your_api_key_here
     ```

2. For GitHub Actions:
   - Follow the instructions in the "Setting Up Secrets for GitHub Workflow" section to add your API key as a secret.

### Important Notes:

- Keep your API key confidential. Don't share it or commit it to version control.
- Use different API keys for development and production environments.
- Monitor your API usage in the Google Cloud Console to avoid unexpected charges.
- Regularly rotate your API keys for security.
- Ensure your billing information is set up in the Google Cloud Console if you expect to exceed the free usage limits.

## Configuring Project Locations

This project uses a JSON configuration file to specify origin and destination locations. Here's how to set it up:

1. Create a file named `locations_config.json` in your project root.

2. Use the following format to specify your locations:

   ```json
   {
     "origins": [
       { "name": "Location1", "lat": 40.7128, "lon": -74.006 },
       { "name": "Location2", "lat": 34.0522, "lon": -118.2437 }
     ],
     "destinations": [
       { "name": "Destination1", "lat": 39.9526, "lon": -75.1652 },
       { "name": "Destination2", "lat": 42.3601, "lon": -71.0589 }
     ]
   }
   ```

3. Replace the example coordinates with your actual origin and destination locations.

4. The project will automatically use this configuration file when running.

Remember to update this file whenever you need to change the set of origins or destinations being considered.

[Rest of the previous content remains unchanged]

# UV Setup and Project Dependencies Guide

This guide will walk you through setting up UV (Ultraviolet) for package management and creating a `pyproject.toml` file for managing project dependencies.

## Installing UV

UV is a modern, fast Python package installer and resolver designed to be a drop-in replacement for pip.

To install UV, run the following command in your terminal:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

This command downloads and runs the UV installer script, which will install UV on your system.

## Setting Up Your Project

Once UV is installed, follow these steps to set up your project:

1. Create a `pyproject.toml` file in your project root directory:

```toml
[project]
name = "public-transport-convenience-calculator"
version = "0.1.0"
description = "A tool to find the best destination for public transport"
requires-python = ">=3.8"

dependencies = [
    "googlemaps",
    "python-dotenv",
    "sqlite3",
]

[project.optional-dependencies]
test = [
    "pytest",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

2. Create a virtual environment using UV:

```bash
uv venv
```

3. Activate the virtual environment:

   On Unix or MacOS:

   ```bash
   source .venv/bin/activate
   ```

   On Windows:

   ```bash
   .venv\Scripts\activate
   ```

4. Install project dependencies:

```bash
uv pip install -e .
```

5. Install test dependencies:

```bash
uv pip install -e ".[test]"
```

## Managing Dependencies

- To add a new dependency, add it to the `dependencies` list in `pyproject.toml`.
- To add a new test dependency, add it to the `test` list under `[project.optional-dependencies]`.
- After modifying `pyproject.toml`, run `uv pip install -e .` to update your environment.

## Running Tests

To run your tests using pytest:

```bash
pytest
```

To run only unit tests (excluding integration tests):

```bash
pytest -m "not integration"
```

## Benefits of Using UV

1. Faster dependency resolution and installation compared to pip.
2. Compatible with modern Python packaging standards.
3. Works well with `pyproject.toml` for dependency management.
4. Provides a consistent environment across different machines.

Remember to keep your `.env` file with sensitive information (like API keys) in your project directory and ensure it's listed in your `.gitignore` file to prevent accidental commits.

name: Python Tests

on:
push:
branches: [ main ]
pull_request:
branches: [ main ]

jobs:
test:
runs-on: ubuntu-latest
strategy:
matrix:
python-version: [3.8, 3.9, '3.10', '3.11']

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install UV
      run: |
        curl -LsSf https://astral.sh/uv/install.sh | sh
        echo "$HOME/.cargo/bin" >> $GITHUB_PATH

    - name: Install dependencies
      run: |
        uv venv
        source .venv/bin/activate
        uv pip install -e ".[test]"

    - name: Run tests
      env:
        GOOGLE_MAPS_API_KEY: ${{ secrets.GOOGLE_MAPS_API_KEY }}
      run: |
        source .venv/bin/activate
        pytest -v -m "not integration"

    - name: Run integration tests
      env:
        GOOGLE_MAPS_API_KEY: ${{ secrets.GOOGLE_MAPS_API_KEY }}
      run: |
        source .venv/bin/activate
        pytest -v -m "integration"

# UV Setup, Project Dependencies, and GitHub CI Guide

[Previous content remains unchanged]

## Setting Up Secrets for GitHub Workflow

When using GitHub Actions for continuous integration, you need to securely store sensitive information like API keys. GitHub Secrets allows you to do this safely. Here's how to set up the secrets for your workflow:

1. Navigate to your GitHub repository.

2. Click on the "Settings" tab at the top of the repository page.

3. In the left sidebar, click on "Secrets and variables", then select "Actions".

4. You'll see a page titled "Actions secrets and variables". Click on the "New repository secret" button.

5. In the "Name" field, enter `GOOGLE_MAPS_API_KEY`. This name should match the secret name used in your GitHub Actions workflow file.

6. In the "Value" field, paste your Google Maps API key.

7. Click "Add secret" to save it.

Now, your GitHub Actions workflow can securely access the API key using `${{ secrets.GOOGLE_MAPS_API_KEY }}` in the workflow file.

### Important Security Notes:

- Never commit your actual API key to the repository.
- Use a different API key for CI than the one you use for local development. This helps maintain separation of environments and limits the potential impact if one key is compromised.
- Regularly rotate your API keys as a security best practice.
- Be mindful of API usage in your CI pipeline to avoid unexpected costs, especially if you're running integration tests that make actual API calls.

### Updating the Secret:

If you need to update the secret (e.g., when rotating API keys):

1. Go to the same "Actions secrets and variables" page in your repository settings.
2. Find the `GOOGLE_MAPS_API_KEY` secret in the list.
3. Click on "Update" to change its value.

Remember, changes to secrets are not versioned, and old workflow runs won't be able to access the updated secret value.

By following these steps, you ensure that your GitHub Actions workflow can securely access the necessary API key without exposing it in your code repository.
