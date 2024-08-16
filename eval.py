import frank_cli

queries = [
    # Example 1: Capital of the United Kingdom
    {"h": "value","v": "?y0","s": "United Kingdom","p": "capital", "o": "?y0"},

    # Example 2: The screenwriter of Mr. Bean
    {"h":"value", "v":"?x", "s":"Mr. Bean", "p":"screenwriter", "o":"?x"},

    # Example 3: Who sang the theme song of Friends
    { "h": "value", "s": "?y0", "p": "sang", "o": "$x3", "v": "?y0",
      "$x3": {"h": "value", "v": "?y0", "s": "Friends", "p": "theme song", "o": "?y0" }},

    # Example 4: How many seasons of Breaking Bad
    {"h":"value", "s":"Breaking Bad", "p":"seasons", "o":"?x", "v":"?x"},

    # Example 5: What is the predicted population of France in 2032
    { "h": "value", "v": "?y0", "s": "France", "p": "population", "o": "?y0", "t": "2032"},

    # Example 6: Is the predicted population of Ghana in 2030 greater than 30000000?
    { "h":"gt", "v":["$x","$y"],    
      "$x": {"h":"value", "v":"?x","s":"Ghana", "p":"population", "o":"?x", "t":"2029"}, 
      "$y": 30000000
    },

    # Example 8: The second highest reorded population of India
    {"h": "rank","v": ["?x",2],"s": "India","p": "population","o": "?x"},

    # Example 9: What has its capital as London and start with "un"
    { "h": "startswith", "v": ["$x", "un"], 
      "$x": {"h": "list","v": "?x","s": "?x","p": "capital","o": "London"}},

    # Example 10: What is the sum of 20000 and 400000 (simple alist)
    { "h":"sum", "v":["$x","$y"], "$x": 20000, "$y": 400000 },

    # Example 10: What is the sum of 20000 and 400000 (nested alist)
    { "h":"sum", "v":["$x","$y"],    
      "$x": {"h":"value", "v":"?x", "?x":20000}, 
      "$y": 400000
    },

    # Example 11: Which country in Europe had the lowest population in 2010?
    { "h": "min", "s": "?x3", "p": "population", "o": "$y0", "v": "$y0", "t": "2010", 
      "?x3": { "$filter": [{"p": "type","o": "country"},{"p": "location","o": "Europe"}]}
    }

]

for query in queries:
    frank_cli.cli(query)

