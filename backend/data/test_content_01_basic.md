# Introduction to Python Programming

## Course Overview

This course introduces fundamental concepts of Python programming for beginners.

### Learning Objectives

- Understand basic Python syntax and data types
- Learn control structures (if/else, loops)
- Work with functions and modules
- Handle basic file operations

## Module 1: Getting Started

### What is Python?

Python is a high-level, interpreted programming language known for:

- **Simple syntax**: Easy to read and write
- **Versatile**: Web development, data science, automation
- **Large ecosystem**: Extensive library support
- **Community**: Active community and resources

### Installing Python

1. Download from python.org
2. Run the installer
3. Verify installation: `python --version`
4. Set up development environment (VSCode, PyCharm)

## Module 2: Basic Syntax

### Variables and Data Types

```python
# Numbers
age = 25
price = 19.99

# Strings
name = "Alice"
message = 'Hello, World!'

# Booleans
is_student = True
is_graduated = False

# Lists
fruits = ["apple", "banana", "orange"]
numbers = [1, 2, 3, 4, 5]
```

### Print and Input

```python
# Output
print("Hello, Python!")

# Input
name = input("Enter your name: ")
print(f"Welcome, {name}!")
```

## Module 3: Control Structures

### Conditional Statements

```python
age = 18

if age >= 18:
    print("You are an adult")
elif age >= 13:
    print("You are a teenager")
else:
    print("You are a child")
```

### Loops

```python
# For loop
for i in range(5):
    print(i)

# While loop
count = 0
while count < 5:
    print(count)
    count += 1
```

## Module 4: Functions

### Defining Functions

```python
def greet(name):
    """Greet a person by name"""
    return f"Hello, {name}!"

def calculate_area(length, width):
    """Calculate rectangle area"""
    return length * width

# Using functions
message = greet("Alice")
area = calculate_area(5, 3)
```

## Module 5: Practice Projects

### Project 1: Simple Calculator

Create a calculator that can:
- Add two numbers
- Subtract two numbers
- Multiply two numbers
- Divide two numbers

### Project 2: To-Do List

Build a console-based to-do list:
- Add tasks
- View tasks
- Mark tasks complete
- Delete tasks

## Summary

Key takeaways from this course:
- Python syntax fundamentals
- Working with data types
- Control flow and decision making
- Creating reusable functions
- Building simple applications

## Next Steps

- Practice with coding exercises
- Explore Python standard library
- Learn about object-oriented programming
- Build personal projects
