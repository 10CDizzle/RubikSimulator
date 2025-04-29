# RubikSimulator

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/)
[![Ursina Engine](https://img.shields.io/badge/engine-Ursina-orange.svg)](https://www.ursinaengine.org/)
<!-- Add other badges if relevant (e.g., license, build status) -->

A 3D Rubik's Cube Simulator built using the Ursina game engine in Python.

## Features

*   Visual representation of a 3x3 Rubik's Cube.
*   Interactive cube rotation controls (details needed - *you might want to add specific keys here*).
*   Basic simulation environment.

## Prerequisites

*   [Python](https://www.python.org/downloads/) (version 3.7 or higher recommended)
*   [pip](https://pip.pypa.io/en/stable/installation/) (usually comes with Python)

## Installation & Setup

Follow these steps to set up the project locally:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/RubikSimulator.git
    cd RubikSimulator
    ```
    *(Replace `YOUR_USERNAME` with your actual GitHub username)*

2.  **Create a virtual environment:**
    *   On Windows:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    *   On macOS/Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *(Using a virtual environment is recommended to keep dependencies isolated.)*

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(If you don't have a `requirements.txt` yet, you can create one after installing Ursina)*

    Alternatively, if you don't have a `requirements.txt`, install Ursina directly:
    ```bash
    pip install ursina
    ```
    *(Consider creating a `requirements.txt` file for easier dependency management: `pip freeze > requirements.txt`)*

## Usage

Once the setup is complete, you can run the simulator:

```bash
python main.py
# RubikSimulator
Basic Rubic's Cube Simulator written with Ursina.
