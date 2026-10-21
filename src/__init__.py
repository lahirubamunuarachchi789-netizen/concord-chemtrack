"""Concord ChemTrack - internal chemical inventory application.

Package layout
--------------
config    : secrets loading, Supabase client factory, schema bootstrap
styles    : global CSS / responsive theme
auth      : login + registration screen and session helpers
inventory : "Chemical Add_on" module (master items, categories, stock entries)
reports   : "Report" module (filters, transaction log, summaries, exports)
ui        : small reusable UI helpers (headers, cards, tables)
"""

__version__ = "1.0.0"
__app_name__ = "Concord ChemTrack"
