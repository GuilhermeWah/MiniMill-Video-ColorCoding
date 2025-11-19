import sys
import os

# Add the project root's 'src' directory to sys.path
# This allows tests to import 'mill_presenter' without installing the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
