#include <iostream>
#include<string>
#include<vector>
#include<unordered_map>
#include<math.h>
using namespace std;
void find_pattern(string se,string pa)
{  int d=2;
   int m=pa.length(),n=se.length();
   long long sum1=0,sum2=0; 
   int c=m-1;
   //below for loop is used to calculate the for the first window
   for(int i=0;i<m;i++)
   { sum1=sum1+(pow(2,c)*se[i]);
     sum2=sum2+(pow(2,c)*pa[i]);
     c=c-1;
   }
   if(sum1==sum2)
   { cout<<0<<" ";
   }
   //below for loop tries to move the window by subtracting a previous element and adding a new element
   //  [1,2,3,4]
   //  [1,2,3]-> first windows
   //  [2,3,4]-> Second window (Here we added one number from the beginnning and added the next element)

   
   for(int i=1;i<(n-m+1);i++)
   {  sum1=d*(sum1-(se[i-1]*pow(2,m-1)))+se[i+m-1]; //This is a formula dervied by rabin karp you can view it
                                                    //here https://www-igm.univ-mlv.fr/~lecroq/string/node5.html
   	  if(sum1==sum2)
   	  { cout<<i<<" ";	
	  }
   }
}
int main() {
	string s1="eksksforgreeks",s2="eks";
	find_pattern(s1,s2);
}
