<img width="360" height="121" alt="image" src="https://github.com/user-attachments/assets/20f8a82a-41d2-4c29-a90a-55da1aa3f21f" /> &nbsp;&nbsp;&nbsp;&nbsp;
<img width="312" height="121" alt="J P  Margin-Logo" src="https://github.com/user-attachments/assets/eeb79cc3-2ead-473d-ac68-076841b48460" />
<br>
**ATTENTION:** This product is not financial advice or any form of an investment suggestion. 
It was created as part of the Structured Products Seminar at the University of Zurich and is purely for educational purposes. The name is a joke and has no affiliations.

# Reverse Convertible Pricing Engine

A simple Python model for pricing reverse convertibles, with or without a barrier.

Volatility is derived from the market price of a call option or entered directly. 
We then calculate the embedded put option and the coupon rate, adjusted for the desired issuer margin.

- Without a barrier: Vanilla put
- With a barrier: Down-and-in put
- Fair value = Present value of the principal and coupon − embedded put

A basic HTML interface sends inputs to a Flask backend and displays the results in JSON format.

The model assumes continuous barrier monitoring and a single coupon payment at maturity.

## Getting Started

In the `code` directory, run:

```bash
python -m pip install flask
python server.py
```

Then, open http://127.0.0.1:8000 in your browser.
