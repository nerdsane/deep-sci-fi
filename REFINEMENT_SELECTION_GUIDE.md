# 🔬 Story Refinement Selection Guide for LangGraph Studio

## **How to Select Your Story Refinement**

After the workflow generates story refinement options using research integration, it will pause and wait for your selection.

### **📋 Step 1: Review Your Options**
The workflow will generate a file called `06_story_refinement_options.md` in your output directory with numbered options like:

```
**Option 1: Research-Driven Character Development**
**Option 2: Technology-Focused World Building**
**Option 3: Scientific Conflict Integration**
```

### **📱 Step 2: Select in LangGraph Studio**
1. **Open the State panel** in LangGraph Studio
2. **Find the `user_refinement_selection` field** 
3. **Enter just the number** of your preferred option (e.g., `2`)
4. **Resume the workflow**

### **✅ Correct Format:**
```json
{
  "user_refinement_selection": 2
}
```

### **❌ Common Mistakes:**
- ❌ Don't paste the full refinement text
- ❌ Don't use quotes around the number 
- ❌ Don't confuse with `user_story_selection` (that's for loglines)

### **🔧 What Happens Next:**
1. The system uses your selected refinement approach
2. Creates detailed outline preparation materials
3. Continues to competitive outline generation
4. Uses the refined story as the foundation for your novel

### **🆘 Troubleshooting:**
- **"Invalid selection number"**: Make sure you're using a number between 1 and the total options shown
- **"Required state missing"**: Make sure the workflow ran successfully through story refinement generation
- **UI shows number/float field**: This is correct! Enter just the number. 