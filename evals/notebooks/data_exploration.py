#%%
import pandas as pd
from pathlib import Path

# Configuration
# Use the complete list as GOLD_SUBS
with open("evals/datasets/ask_subreddits_complete.txt", "r") as f:
    GOLD_SUBS = {line.strip() for line in f if line.strip()}

GOLD_SUBS.update(["science","biology","movies", "books", "technology", "gardening", "comics", "worldnews", "television"])
print(f"GOLD_SUBS now has {len(GOLD_SUBS)} Ask subreddits")
MIN_POST_SCORE = 500
MIN_NUM_COMMENTS = 30
MIN_COMMENT_SCORE = 5
TOP_N_COMMENTS = 10
MAX_TOKENS = 10000
MAX_POSTS_PER_SUB = 600

DATASETS_DIR = Path("evals/datasets")
PROCESSED_DIR = Path("evals/processed")

def estimate_tokens(text):
    if not text:
        return 0
    return len(str(text)) // 3

print("Configuration loaded")
# %%
import matplotlib.pyplot as plt

print("Loading posts...")
posts_df = pd.read_parquet(DATASETS_DIR / "RS_2016-02_00.parquet")
print(f"Total posts: {len(posts_df)}")

posts_df = posts_df[posts_df['subreddit'].isin(GOLD_SUBS)]
print(f"After subreddit filter: {len(posts_df)}")

# Track subreddit counts at each step
subreddit_counts_initial = posts_df['subreddit'].value_counts()

posts_df = posts_df[
    (posts_df['score'] >= MIN_POST_SCORE) &
    (posts_df['num_comments'] >= MIN_NUM_COMMENTS)
]
print(f"After score/comments filter: {len(posts_df)}")
subreddit_counts_after_score = posts_df['subreddit'].value_counts()

posts_df = posts_df[
    posts_df['title'].notna() &
    (posts_df['title'] != '') &
    posts_df['selftext'].notna() &
    (posts_df['selftext'] != '')
]
print(f"After empty text filter: {len(posts_df)}")
subreddit_counts_after_text = posts_df['subreddit'].value_counts()

posts_df['title_lower'] = posts_df['title'].str.lower()
posts_df = posts_df.drop_duplicates(subset=['subreddit', 'title_lower'])
posts_df = posts_df.drop(columns=['title_lower'])
print(f"After deduplication: {len(posts_df)}")

keep_fields = ['id', 'subreddit', 'title', 'selftext', 'score', 'num_comments', 'created_utc']
if 'link_flair_text' in posts_df.columns:
    keep_fields.append('link_flair_text')
posts_df = posts_df[keep_fields]
print(f"Final posts shape: {posts_df.shape}")

kept_post_ids = set(posts_df['id'].values)
print(f"Post IDs for comment filtering: {len(kept_post_ids)}")

# Create bar graph showing subreddit counts
final_counts = posts_df['subreddit'].value_counts()
plt.figure(figsize=(15, 8))
final_counts.plot(kind='bar')
plt.title('Posts per Subreddit (After All Filters)')
plt.xlabel('Subreddit')
plt.ylabel('Number of Posts')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()

print(f"\nSubreddit breakdown:")
print(final_counts)
# %%

import pyarrow.parquet as pq

print("Loading comments in chunks...")

kept_post_ids_str = set("t3_" + str(x) for x in kept_post_ids)  # Ensure string type for matching
comments_path = DATASETS_DIR / "RC_2016-02.parquet"
comments = []
batch_size = 100_000

for batch in pq.ParquetFile(comments_path).iter_batches(batch_size=batch_size):
    df = pd.DataFrame(batch.to_pandas())
    # Filter for relevant posts only
    df = df[df['link_id'].isin(kept_post_ids_str)]
    # Filter out deleted/removed/empty comments
    df = df[
        df['body'].notna() &
        (df['body'] != '') &
        (~df['body'].isin(['[deleted]', '[removed]']))
    ]
    # Filter by score
    df = df[df['score'] >= MIN_COMMENT_SCORE]
    if not df.empty:
        comments.append(df)
    print(f"Loaded {len(df)} matching comments in this batch")

if comments:
    comments_df = pd.concat(comments, ignore_index=True)
else:
    comments_df = pd.DataFrame(columns=['id', 'link_id', 'body', 'score', 'created_utc'])

print(f"Total filtered comments: {len(comments_df)}")

# Keep only needed fields
keep_fields = ['id', 'link_id', 'body', 'score', 'created_utc']
if 'author_flair_text' in comments_df.columns:
    keep_fields.append('author_flair_text')
comments_df = comments_df[keep_fields]

print(f"Selecting top {TOP_N_COMMENTS} comments per post...")
top_comments = (
    comments_df
    .sort_values(['link_id', 'score'], ascending=[True, False])
    .groupby('link_id')
    .head(TOP_N_COMMENTS)
    .reset_index(drop=True)
)
print(f"Final comments: {len(top_comments)}")
# %%
# Fix the link_id format by removing the t3_ prefix
top_comments['link_id'] = top_comments['link_id'].str.replace('t3_', '', regex=False)

# Now group comments by post
comments_grouped = top_comments.groupby('link_id').apply(
    lambda x: x.drop('link_id', axis=1).to_dict('records')
).to_dict()

# Add comments to posts
posts_df['comments'] = posts_df['id'].map(comments_grouped)
posts_df['comments'] = posts_df['comments'].apply(lambda x: x if isinstance(x, list) else [])

# Verify the fix
print(f"Posts with comments: {sum(posts_df['comments'].apply(len) > 0)}")
print(f"Total comments attached: {sum(posts_df['comments'].apply(len))}")

# Apply token limit filter
def check_token_limit(row):
    title_tokens = estimate_tokens(row['title'])
    selftext_tokens = estimate_tokens(row['selftext'])
    comments = row['comments'] if isinstance(row['comments'], list) else []
    comments_tokens = sum(estimate_tokens(c['body']) for c in comments)
    total_tokens = title_tokens + selftext_tokens + comments_tokens
    return total_tokens <= MAX_TOKENS

print("Applying token limit filter...")
posts_df = posts_df[posts_df.apply(check_token_limit, axis=1)]
print(f"After token limit: {len(posts_df)}")

# Limit posts per subreddit
print(f"Limiting to {MAX_POSTS_PER_SUB} posts per subreddit...")
final_posts = []
for subreddit in GOLD_SUBS:
    sub_posts = posts_df[posts_df['subreddit'] == subreddit].head(MAX_POSTS_PER_SUB)
    final_posts.append(sub_posts)
    print(f"{subreddit}: {len(sub_posts)} posts")

final_df = pd.concat(final_posts, ignore_index=True)
print(f"Final dataset: {len(final_df)} posts")

# Summary stats
print("\nSummary by subreddit:")
print(final_df.groupby('subreddit').size())
# %%
PROCESSED_DIR.mkdir(exist_ok=True)
output_path = PROCESSED_DIR / "reddit_2016_filtered_complete.parquet"
final_df.to_parquet(output_path, index=False)
print(f"Processed dataset saved to: {output_path}")
print(f"Dataset shape: {final_df.shape}")
print("Processing complete!")