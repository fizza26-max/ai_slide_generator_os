import streamlit as st
import language_tool_python
from typing import List, Dict, Tuple
import re
from collections import Counter

# Blue and White Theme CSS
CUSTOM_CSS = """
<style>
    /* Main theme colors */
    :root {
        --primary-blue: #0B69FF;
        --secondary-blue: #1E40AF;
        --light-blue: #DBEAFE;
        --lighter-blue: #EFF6FF;
        --white: #FFFFFF;
        --text-dark: #1F2937;
        --text-gray: #6B7280;
        --success-green: #10B981;
        --warning-yellow: #F59E0B;
        --error-red: #EF4444;
    }
    
    /* Main app background */
    .stApp {
        background: linear-gradient(135deg, #FFFFFF 0%, #EFF6FF 100%);
    }
    
    /* Headers */
    h1 {
        color: var(--secondary-blue) !important;
        font-weight: 700 !important;
        padding-bottom: 1rem;
        border-bottom: 3px solid var(--primary-blue);
    }
    
    h2, h3 {
        color: var(--secondary-blue) !important;
        font-weight: 600 !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--secondary-blue) 0%, var(--primary-blue) 100%);
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stCheckbox label,
    [data-testid="stSidebar"] .stSlider label {
        color: white !important;
        font-weight: 500 !important;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        color: var(--primary-blue) !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: var(--text-gray) !important;
        font-weight: 600 !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, var(--primary-blue) 0%, var(--secondary-blue) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        transition: transform 0.2s, box-shadow 0.2s !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(11, 105, 255, 0.4) !important;
    }
    
    /* Text areas */
    .stTextArea textarea {
        border: 2px solid var(--light-blue) !important;
        border-radius: 8px !important;
        font-size: 1rem !important;
    }
    
    .stTextArea textarea:focus {
        border-color: var(--primary-blue) !important;
        box-shadow: 0 0 0 3px rgba(11, 105, 255, 0.1) !important;
    }
    
    /* Info boxes */
    .stAlert {
        border-radius: 8px !important;
        border-left: 4px solid var(--primary-blue) !important;
    }
    
    /* Download button */
    .stDownloadButton > button {
        background: var(--success-green) !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    
    /* Custom card styling */
    .custom-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        border-left: 4px solid var(--primary-blue);
        margin-bottom: 1rem;
    }
    
    .error-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid var(--error-red);
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
    }
    
    .suggestion-card {
        background: var(--lighter-blue);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid var(--primary-blue);
        margin-bottom: 0.75rem;
    }
</style>
"""

# Initialize session state
if 'checked_text' not in st.session_state:
    st.session_state.checked_text = ""
if 'corrections' not in st.session_state:
    st.session_state.corrections = []
if 'corrected_text' not in st.session_state:
    st.session_state.corrected_text = ""

@st.cache_resource(show_spinner=False)
def load_grammar_tool(language: str = "en-US"):
    """Load and cache the LanguageTool grammar checker"""
    return language_tool_python.LanguageTool(language)

def categorize_error(rule_id: str, category: str) -> str:
    """Categorize errors into user-friendly types"""
    if "SPELL" in rule_id or "MORFOLOGIK" in rule_id:
        return "Spelling"
    elif "PUNCT" in rule_id or "COMMA" in rule_id:
        return "Punctuation"
    elif "GRAMMAR" in rule_id or category == "GRAMMAR":
        return "Grammar"
    elif "STYLE" in rule_id or category == "STYLE":
        return "Style"
    elif "TYPO" in rule_id:
        return "Typo"
    else:
        return "Other"

def check_grammar(text: str, tool: language_tool_python.LanguageTool) -> List[Dict]:
    """Check grammar and return structured results"""
    matches = tool.check(text)
    results = []
    
    for match in matches:
        error_type = categorize_error(match.ruleId, match.category)
        
        result = {
            "message": match.message,
            "context": match.context,
            "offset": match.offset,
            "length": match.errorLength,
            "replacements": match.replacements[:3] if match.replacements else [],
            "type": error_type,
            "rule_id": match.ruleId,
            "sentence": match.sentence
        }
        results.append(result)
    
    return results

def apply_corrections(text: str, corrections: List[Dict]) -> str:
    """Apply all corrections to the text"""
    # Sort corrections by offset in reverse order to maintain positions
    sorted_corrections = sorted(corrections, key=lambda x: x['offset'], reverse=True)
    
    corrected = text
    for corr in sorted_corrections:
        if corr['replacements']:
            start = corr['offset']
            end = start + corr['length']
            corrected = corrected[:start] + corr['replacements'][0] + corrected[end:]
    
    return corrected

def calculate_readability_score(text: str) -> Dict:
    """Calculate basic readability metrics"""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    words = text.split()
    word_count = len(words)
    sentence_count = len(sentences)
    
    if sentence_count == 0:
        return {"words": 0, "sentences": 0, "avg_words": 0}
    
    avg_words_per_sentence = word_count / sentence_count
    
    return {
        "words": word_count,
        "sentences": sentence_count,
        "avg_words": round(avg_words_per_sentence, 1)
    }

def get_error_icon(error_type: str) -> str:
    """Get emoji icon for error type"""
    icons = {
        "Spelling": "📝",
        "Grammar": "📚",
        "Punctuation": "❗",
        "Style": "✨",
        "Typo": "⌨️",
        "Other": "🔍"
    }
    return icons.get(error_type, "🔍")

# Page configuration
st.set_page_config(
    page_title="AI Grammar Checker",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Header
st.title("✍️ AI Grammar Checker Agent")
st.markdown("**Powered by AI** • Check grammar, spelling, punctuation, and style in real-time")

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    language = st.selectbox(
        "Language",
        ["en-US", "en-GB", "en-CA", "en-AU"],
        index=0,
        help="Select the language variant for grammar checking"
    )
    
    show_categories = st.multiselect(
        "Show Error Types",
        ["Spelling", "Grammar", "Punctuation", "Style", "Typo", "Other"],
        default=["Spelling", "Grammar", "Punctuation", "Style", "Typo", "Other"],
        help="Filter which types of errors to display"
    )
    
    auto_correct = st.checkbox(
        "Auto-apply first suggestion",
        value=False,
        help="Automatically apply the first suggested correction"
    )
    
    show_stats = st.checkbox(
        "Show Statistics",
        value=True,
        help="Display text statistics and metrics"
    )
    
    st.markdown("---")
    st.markdown("### 📖 About")
    st.markdown("""
    This AI Grammar Checker uses advanced natural language processing to:
    - ✅ Detect spelling errors
    - ✅ Fix grammar mistakes
    - ✅ Improve punctuation
    - ✅ Enhance writing style
    - ✅ Provide smart suggestions
    """)
    
    st.markdown("---")
    st.markdown("### 💡 Tips")
    st.markdown("""
    - Paste or type your text
    - Click **Check Grammar**
    - Review suggestions
    - Apply corrections
    - Download corrected text
    """)

# Main content area
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("### 📝 Your Text")
    
    # Sample text button
    if st.button("📄 Load Sample Text"):
        sample_text = """This is a sample text with some erors. It contain grammar mistakes and spelling problems. The AI grammar checker will helps you fix this issues. You can see all the suggestion's and apply them to improve you're writing. Its a powerful tool for writers, students and professionals."""
        st.session_state.checked_text = sample_text
    
    # Text input
    input_text = st.text_area(
        "Enter or paste your text here",
        value=st.session_state.checked_text,
        height=400,
        placeholder="Start typing or paste your text here...",
        label_visibility="collapsed"
    )
    
    # Action buttons
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    
    with col_btn1:
        check_button = st.button("🔍 Check Grammar", use_container_width=True)
    
    with col_btn2:
        clear_button = st.button("🗑️ Clear", use_container_width=True)
    
    with col_btn3:
        if st.session_state.corrected_text:
            st.download_button(
                "💾 Download",
                data=st.session_state.corrected_text,
                file_name="corrected_text.txt",
                mime="text/plain",
                use_container_width=True
            )

with col2:
    st.markdown("### 🎯 Results")
    
    if clear_button:
        st.session_state.checked_text = ""
        st.session_state.corrections = []
        st.session_state.corrected_text = ""
        st.rerun()
    
    if check_button and input_text.strip():
        with st.spinner("🔄 Analyzing your text..."):
            # Load grammar tool
            tool = load_grammar_tool(language)
            
            # Check grammar
            corrections = check_grammar(input_text, tool)
            
            # Filter by selected categories
            corrections = [c for c in corrections if c['type'] in show_categories]
            
            # Store in session state
            st.session_state.checked_text = input_text
            st.session_state.corrections = corrections
            
            # Apply corrections if auto-correct is enabled
            if auto_correct:
                st.session_state.corrected_text = apply_corrections(input_text, corrections)
            else:
                st.session_state.corrected_text = input_text
    
    # Display results
    if st.session_state.corrections or st.session_state.checked_text:
        if not st.session_state.corrections:
            st.success("✅ **Perfect!** No grammar issues found.")
            st.balloons()
        else:
            # Statistics
            if show_stats:
                stats = calculate_readability_score(st.session_state.checked_text)
                error_counts = Counter([c['type'] for c in st.session_state.corrections])
                
                st.markdown("#### 📊 Statistics")
                metric_cols = st.columns(4)
                
                with metric_cols[0]:
                    st.metric("Total Errors", len(st.session_state.corrections))
                
                with metric_cols[1]:
                    st.metric("Words", stats['words'])
                
                with metric_cols[2]:
                    st.metric("Sentences", stats['sentences'])
                
                with metric_cols[3]:
                    st.metric("Avg Words/Sentence", stats['avg_words'])
                
                st.markdown("---")
            
            # Error breakdown
            st.markdown("#### 🔍 Issues Found")
            
            error_counts = Counter([c['type'] for c in st.session_state.corrections])
            
            # Display error type summary
            summary_cols = st.columns(len(error_counts))
            for idx, (error_type, count) in enumerate(error_counts.items()):
                with summary_cols[idx]:
                    st.markdown(f"""
                    <div class="custom-card" style="text-align: center;">
                        <div style="font-size: 2rem;">{get_error_icon(error_type)}</div>
                        <div style="font-size: 1.5rem; color: var(--primary-blue); font-weight: 700;">{count}</div>
                        <div style="color: var(--text-gray); font-size: 0.9rem;">{error_type}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Display individual corrections
            st.markdown("#### 📋 Detailed Suggestions")
            
            for idx, correction in enumerate(st.session_state.corrections, 1):
                icon = get_error_icon(correction['type'])
                
                with st.expander(f"{icon} **{correction['type']}** - {correction['message'][:60]}...", expanded=(idx <= 3)):
                    st.markdown(f"**Issue:** {correction['message']}")
                    
                    # Show context
                    context = correction['context']
                    st.markdown(f"**Context:** ...{context}...")
                    
                    # Show suggestions
                    if correction['replacements']:
                        st.markdown("**Suggestions:**")
                        for i, replacement in enumerate(correction['replacements'], 1):
                            st.markdown(f"{i}. `{replacement}`")
                    else:
                        st.info("No automatic suggestions available.")
            
            # Show corrected text
            if auto_correct and st.session_state.corrected_text:
                st.markdown("---")
                st.markdown("#### ✨ Corrected Text")
                st.text_area(
                    "Corrected version",
                    value=st.session_state.corrected_text,
                    height=300,
                    label_visibility="collapsed"
                )
    else:
        st.info("👆 Enter text and click **Check Grammar** to get started!")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: var(--text-gray); padding: 2rem 0;">
    <p><strong>AI Grammar Checker Agent</strong> • Built with ❤️ using Streamlit & LanguageTool</p>
    <p style="font-size: 0.9rem;">Blue & White Theme • Fast • Accurate • Privacy-Focused</p>
</div>
""", unsafe_allow_html=True)
