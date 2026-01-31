"""
Call Transcripts API - Retrieve stored call transcripts with analytics
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from db.connection import get_db
from db.schemas import CallTranscript

router = APIRouter(prefix="/api/calls", tags=["calls"])


@router.get("/transcripts", response_model=List[dict])
async def get_call_transcripts(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    call_source: Optional[str] = Query(None, description="Filter by call source (web/twilio)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip for pagination")
):
    """
    Get call transcripts with AI-generated summaries and satisfaction scores.
    
    Returns calls sorted by most recent first.
    """
    try:
        db = get_db()
        
        # Build query filter
        query_filter = {}
        if user_id:
            query_filter["user_id"] = user_id
        if call_source:
            query_filter["call_source"] = call_source
        
        # Query database
        cursor = db.call_transcripts.find(query_filter).sort("start_time", -1).skip(skip).limit(limit)
        transcripts = await cursor.to_list(length=limit)
        
        # Serialize ObjectId
        for transcript in transcripts:
            if "_id" in transcript:
                transcript["_id"] = str(transcript["_id"])
        
        return transcripts
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve transcripts: {str(e)}")


@router.get("/transcripts/{call_id}", response_model=dict)
async def get_call_transcript(call_id: str):
    """
    Get a specific call transcript by call ID.
    """
    try:
        db = get_db()
        transcript = await db.call_transcripts.find_one({"call_id": call_id})
        
        if not transcript:
            raise HTTPException(status_code=404, detail=f"Call transcript not found: {call_id}")
        
        # Serialize ObjectId
        if "_id" in transcript:
            transcript["_id"] = str(transcript["_id"])
        
        return transcript
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve transcript: {str(e)}")


@router.get("/analytics/summary")
async def get_call_analytics_summary(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze")
):
    """
    Get aggregated analytics for calls:
    - Total calls
    - Average satisfaction score
    - Average call duration
    - Language distribution
    """
    try:
        db = get_db()
        
        # Build query filter
        query_filter = {}
        if user_id:
            query_filter["user_id"] = user_id
        
        # Get calls from last N days
        from datetime import timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        query_filter["start_time"] = {"$gte": start_date}
        
        # Aggregate statistics
        pipeline = [
            {"$match": query_filter},
            {
                "$group": {
                    "_id": None,
                    "total_calls": {"$sum": 1},
                    "avg_satisfaction": {"$avg": "$satisfaction_score"},
                    "avg_duration": {"$avg": "$duration_seconds"},
                    "languages": {"$push": "$detected_language"}
                }
            }
        ]
        
        result = await db.call_transcripts.aggregate(pipeline).to_list(length=1)
        
        if not result:
            return {
                "total_calls": 0,
                "avg_satisfaction_score": 0,
                "avg_duration_seconds": 0,
                "language_distribution": {}
            }
        
        stats = result[0]
        
        # Calculate language distribution
        languages = stats.get("languages", [])
        lang_dist = {}
        for lang in languages:
            lang_dist[lang] = lang_dist.get(lang, 0) + 1
        
        return {
            "total_calls": stats.get("total_calls", 0),
            "avg_satisfaction_score": round(stats.get("avg_satisfaction", 0), 2),
            "avg_duration_seconds": round(stats.get("avg_duration", 0), 1),
            "language_distribution": lang_dist,
            "period_days": days
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve analytics: {str(e)}")
