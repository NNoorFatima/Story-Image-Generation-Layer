# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up your API keys
cp .env.example .env
# Edit .env → add your GROQ_API_KEY and HF_API_KEY

# 3. Run interactively
python main.py

# Or directly
python main.py --mode auto --input "Your story idea here"
