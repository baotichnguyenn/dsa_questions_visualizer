### Nested cryptographic transcript 
A cryptographic protocol may execute several proof components inside one another. An audit system records the beginning and end of each component in a transcript 
E[0], E[1], . . . , E[n − 1]. 
Each entry has one of the following forms: open(k),  meaning that the proof component with identifier k begins, 
or  
close(k),  meaning that the proof component with identifier k ends. 
Every identifier appears in at most one open event and at most one close event. A transcript is valid when both of the following conditions hold: 
1. Every close(k) event matches the most recently opened component that has not already been closed. 
2. Every opened component is closed before the transcript ends. 
The number of components that are open at the same time is called the current nesting depth. The largest nesting depth reached anywhere in the transcript is called the maximum nesting depth. 
The algorithm must return one of the following outputs: 
1.  (valid, d):  where d is the maximum nesting depth, if the transcript is valid. 
2.  (invalid, i): where i is the index of the first close event that cannot be matched correctly. Transcript indices start at 0. 
3.  Incomplete: if every close event is matched correctly, but one or more components remain open when the transcript ends. 
The transcript may be empty. The empty transcript is valid and has maximum nesting depth 0. 
Examples. 
1. For the transcript 
E = [ open(7), open(3), close(3), 
open(9), close(9), close(7)], 
the correct output is  (valid, 2). 
2. For the transcript 
E = [open(7), open(3), close(7), close(3)], 
the correct output is  (invalid, 2), 
because component 3 must be closed before component 7. 
3. For the transcript 
E = [open(7), open(3), close(3)], 
the correct output is  incomplete,  because component 7 remains open. 
