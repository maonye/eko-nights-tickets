"""Made-up seed data for the fictional organiser Eko Nights.

Every name, venue and price here is invented for the exercise.
"""
from __future__ import annotations

EVENTS = [
    {"event_id": "EVT-AFRO", "name": "Eko Nights: Afrobeats Under the Stars",
     "venue": "The Garden Courtyard, Lekki Phase 1, Lagos",
     "starts_at": "2026-12-12T19:00:00+01:00", "doors_open": "17:30",
     "organiser": "Eko Nights", "verified": "TRUE", "on_sale": "TRUE", "age_limit": "18",
     "description": "Open-air Afrobeats night with three live acts and a DJ set till late."},
    {"event_id": "EVT-COMEDY", "name": "Eko Nights Comedy Special",
     "venue": "Harbour Hall, Victoria Island, Lagos",
     "starts_at": "2026-12-19T18:00:00+01:00", "doors_open": "17:00",
     "organiser": "Eko Nights", "verified": "TRUE", "on_sale": "TRUE", "age_limit": "16",
     "description": "Two hours of stand-up from five comedians. Seating is free, first come first served."},
    {"event_id": "EVT-UNVERIFIED", "name": "Detty December Mega Rave",
     "venue": "To be announced",
     "starts_at": "2026-12-27T20:00:00+01:00", "doors_open": "",
     "organiser": "Unknown promoter", "verified": "FALSE", "on_sale": "TRUE", "age_limit": "18",
     "description": "Submitted by a third-party promoter and not yet verified. Must never be sold."},
]

TIERS = [
    {"tier_id": "AFRO-REG", "event_id": "EVT-AFRO", "name": "Regular", "price_ngn": "15000",
     "capacity": "300", "max_per_order": "6", "perks": "General admission"},
    {"tier_id": "AFRO-VIP", "event_id": "EVT-AFRO", "name": "VIP", "price_ngn": "45000",
     "capacity": "40", "max_per_order": "4", "perks": "Raised deck, fast-lane entry, one welcome drink"},
    {"tier_id": "COMEDY-FRONT", "event_id": "EVT-COMEDY", "name": "Front Row", "price_ngn": "25000",
     "capacity": "2", "max_per_order": "2", "perks": "Front two rows. Expect to be part of the show."},
    {"tier_id": "RAVE-REG", "event_id": "EVT-UNVERIFIED", "name": "Regular", "price_ngn": "5000",
     "capacity": "1000", "max_per_order": "10", "perks": ""},
]


def seed_memory(store) -> None:
    store.append_many("events", EVENTS)
    store.append_many("tiers", TIERS)
