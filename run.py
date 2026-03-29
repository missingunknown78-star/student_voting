from student.models import Vote
from admin.models import Candidate
import json

election_id = 33

# Get all candidates for this election sorted by ID
all_candidates = Candidate.query.filter_by(election_id=election_id)\
                                .order_by(Candidate.id).all()
sorted_candidate_ids = [c.id for c in all_candidates]

print(f"📋 Sorted candidate IDs for election {election_id}:")
print(sorted_candidate_ids)
print()

# Get all votes for this election
votes = Vote.query.filter_by(election_id=election_id).all()
print(f"📊 Found {len(votes)} votes")

fixed_count = 0
for vote in votes:
    if vote.finder_hash:
        try:
            finder_data = json.loads(vote.finder_hash)
            
            # Check if candidate_order already exists
            if 'candidate_order' not in finder_data:
                # Add candidate_order
                finder_data['candidate_order'] = sorted_candidate_ids
                
                # Save back
                vote.finder_hash = json.dumps(finder_data)
                fixed_count += 1
                print(f"✅ Fixed vote {vote.id}")
                
        except Exception as e:
            print(f"❌ Error fixing vote {vote.id}: {e}")

db.session.commit()
print(f"\n✅ Fixed {fixed_count} out of {len(votes)} votes")
print("Now all votes have candidate_order!")