/*
* Last Name:    Champagne
* First Name:   Steven
* UCID:         
* Course:       CPSC526
* Tutorial:     T03
* Assignemnt:   5
* Date:         NOV. 23, 2017
*
*
* How to Compile / Run:
*   COMPILE:        g++ fw.cpp -o fw -std=c++11
*   RUN:            fw rules.txt < packets.txt
*
*   RUN WITH DIFF: ./fw rules.txt < packets.txt | diff -y results.txt -
*/

#include <cstdlib>       // exit()
#include <stdint.h>     //uint16_t range:0...65535 , uint32_t range:0...4294967295
#include <iostream>
#include <string>
#include <fstream>      //.is_open()    //.eof()
#include <sstream>      //istringstream //.>>

#define MAXIMUM_NUMBER_OF_RULES 4096

using namespace std;

// need to fix this to be in accrodance with outputs described.
static void notifyMalformed(unsigned int lineNumber, string reason){
    // if malformatted rule discard it.
    cout    << "Error detected in rules file. LINE#: "<<lineNumber
            << ", Reason: "<< reason
            << ".  Discarding Rule."<<endl;
}

// if no rule matches: print dropped packet.
// inputs: d=direction, i=ip, p=port, f=flag.
static void printPacketDropped(string d, string i, string p, string f){
    cout << "drop() " << d << " " << i << " " << p << " " << f << endl;
}

class Rule {
    public:
        //// PROTOTYPES ////

        // constructor
        Rule(unsigned int r, unsigned int l); // r is rule number, l is line number form file.

        // prototypes for getters
        unsigned int get_RuleNumber();
        unsigned int get_LineNumber();

        // prototypes to set data from strings from file lines
        bool set_Direction(string direction);
        bool set_Action(string action);
        bool set_IpAndNm(string ip);
        bool set_Ports(string port);
        void set_Established();

        //packet checking functions
        bool assessPacket(string d, string i, string p, string f);
        bool compareIPs(uint32_t p_ip);
        bool comparePorts(string packet_port);
        //bool compareEstablished(string packet_flag);

        //internal data manipulation functions
        bool convertStringIPtoHEX(string ip_string, uint32_t& ip_hex);

        //debuggers
        void debugRule_D(); // data version of debug function.
        void debugRule_S(); // string version of debug function.

        // stdout printers
        void printDecision(string d, string i, string p, string f);

    private:
        //// CONVERTED DATA MEMBERS ////
        unsigned int ruleNumber;    // index in the rule array that the rule is in.
        unsigned int lineNumber;    // line in the file where the rule came from.
        bool direction;             // 0 = in, 1 = out
        bool action;                // 0 = accept, 1 = reject;
        uint32_t ip;                // hex form of ip
        int cidrTag =-999;         // the # from 0.0.0.0/#
        uint32_t netmask;           // hex form of netmask
        bool flag = false;          // 0 if not established, 1 if established.

        //// ORIGINAL STRING MEMBERS ////
        string direction_s;
        string action_s;
        string ip_s;
        string port_s;
        string flag_s = "";
};

// default ctor definition
Rule::Rule(unsigned int r, unsigned int l){
    this->ruleNumber=r;
    this->lineNumber=l;
}

unsigned int Rule::get_RuleNumber(){
    return this->ruleNumber;
}

unsigned int Rule::get_LineNumber(){
    return this->lineNumber;
}

void Rule::set_Established(){
    this->flag_s="established";
    this->flag=true;
}

// sets direction to 0 for in, or 1 for out. if not in or out returns false.
bool Rule::set_Direction(string direction){
    this->direction_s = direction;

    if (! direction.compare("in")){
        this->direction=0;
        return true;
    }
    else if(! direction.compare("out")){
        this->direction=1;
        return true;
    }
    else{
        return false;
    }

}

// if action is accept sets rule.action to 0, if reject sets to 1.
// returns false if neither accept or reject.
bool Rule::set_Action(string action){
    this->action_s = action;

    if (! action.compare("accept")){
        this->action=0;
        return true;
    }
    else if(! action.compare("reject")){
        this->action=1;
        return true;
    }
    else{
        return false;
    }
}


// checks if the ip is in the form a.b.c.d/e or '*' and saves the result to the class.
bool Rule::set_IpAndNm(string ip){
    this->ip_s = ip;

    char ch;
    bool state = false;
    uint32_t a,b,c,d,e;
    istringstream iss(ip);


    //cout <<"IP: "<< ip<< " ";

    // first check if it is a star (meaning any)
    if(iss.peek() == '*'){
        //cout << "FOUND IP STAR"<<endl;//del
        state = true;//do not return here.
    }

    //make sure the ip address conforms to a.b.c.d format. eg 10.101.12.99
    else if((iss>>a>>ch>>b>>ch>>c>>ch>>d)){
        state = true;
        // make the hex number for the ip here and save it.
        this->ip = (a<<24)+(b<<16)+(c<<8)+d;
        //cout << "HEXIP: "<< hex << this->ip <<endl;
    }

    //cout<<dec<<"A:"<<a<<" B:"<<b<<" C:"<<c<<" D:"<<d<<" "<<endl;//del

    // get the cidr integer if it exists. eg. a.b.c.d/e
    if((state == true) && (iss>>ch>>e)){
        this->cidrTag=e;

        //make a netmask from the CIDR tag.
        if (e > 32 || e < 0){
            //cider tag can not be greater than 32 or negative.
            return false;
        }
        else if(e == 32){
            this->netmask = 0xFFFFFFFF;
        }
        else{
            this->netmask = 0xFFFFFFFF << (32 - e);
        }

        //cout<<hex<<"NM: "<<netmask<<endl;//del
        //cout<<dec<<" CIDR:"<<e<<endl;//del
    }
    //cout<<endl;//del

    return state;
}


bool Rule::set_Ports(string port){
    this->port_s = port;
    // could do more checking if correct input here... oh well.
    return true;
}


void Rule::debugRule_D(){
    cout<<dec<<"\tDIR: "<<direction<<" ACT:"<<action<<hex<<"  IP:"<<ip
        <<" CT:"<<dec<<cidrTag<<hex<<" NM:"<<netmask<<dec<<" F:"<<flag
        <<endl;
}


void Rule::debugRule_S(){
    // tostring function essentially.
    cout    << "rule[" << ruleNumber<< "] " << " line(" << lineNumber << "):"
            <<direction_s << " " << action_s << " " << ip_s << " "
            << port_s << " " << flag_s << endl;
}




// main
int main(int argc, char** argv){

    // if not right number of args, exit.
    if (argc != 2){
        cout << "PROPER USE EXAMPLE: ./fw rules.txt < packets.txt"<<endl;
        exit(-1);
    }

    // try to open the file
    string FILE(argv[1]);
    ifstream fin(FILE);
    unsigned int ruleNumber = 0, lineNumber = 0;

    Rule* rules_ptr[MAXIMUM_NUMBER_OF_RULES];

    if(fin.is_open()){
        while(!fin.eof()){
            lineNumber++;

            // If rules file is very large then quit.
            if (lineNumber > MAXIMUM_NUMBER_OF_RULES){
                cout<<"EXCEEDED MAXIMUM NUMBER OF RULES: "<<MAXIMUM_NUMBER_OF_RULES;
                exit(-1);
            }

            // setup file parse for this line.
            string line;
            std::getline(fin, line);
            stringstream ss(line);
            string direction, action, ip, port, flag;

            // check if line is empty. if it is skip it.
            if(!(ss >> direction)){
                cout<<"EMPTY LINE. EXCLUDE LINE# : "<<lineNumber<<endl;//del
                continue;
            }

            // check if first non whitespace char is a #. if it is skip it.
            if (direction.at(0) == '#' ){
                cout<<"COMMENT. EXCLUDE LINE# : "<<lineNumber<<endl;//del
                continue;
            }

            // need to check if rule has proper fields.
            if(!(ss >> action >> ip >> port)){
                if(ss.eof()){
                    //if line == EOF, do nothing.
                    continue;
                }
                else{
                    notifyMalformed(lineNumber,"Improper Fields");
                    continue;
                }
            }

            // allocate memory for a new rule.
            Rule* new_rule = new Rule(ruleNumber, lineNumber);

            // need to convert strings in file parse to rule data fields.
            if (! new_rule->set_Direction(direction)){
                notifyMalformed(lineNumber, direction);
                delete new_rule;
                continue;
            }
            if (! new_rule->set_Action(action)){
                notifyMalformed(lineNumber, action);
                delete new_rule;
                continue;
            }
            if (! new_rule->set_IpAndNm(ip)){
                notifyMalformed(lineNumber, ip);
                delete new_rule;
                continue;
            }
            if (! new_rule->set_Ports(port)){
                notifyMalformed(lineNumber, port);
                delete new_rule;
                continue;
            }

            // got here if rule was good form.
            rules_ptr[ruleNumber] = new_rule;

            // if flag is established, then flag=true. Note: remember string.compare returns 0 if matches!!
            if(ss >> flag && !flag.compare("established")){
                rules_ptr[ruleNumber]->set_Established();
            }

            ruleNumber++;
        }
    }
    else{
        cout<<"ERROR OPENING THE RULES FILE."<<endl;
        exit(-1);
    }
    fin.close();

    //// OPENING RULES FILE DONE ////


    // TEST PRINT RULES (DEBUG ONLY)
    // for(unsigned int i = 0; i < ruleNumber; i++){
    //     rules_ptr[i]->debugRule_S();
    //     rules_ptr[i]->debugRule_D();
    // }

    //// READ THE PACKETS FILE FROM STDIO////
        // ASSUMES NO MALFORMED PACKETS //
    while(!std::cin.eof()){
        string line;
        std::getline(std::cin, line);
        stringstream ss(line);

        // if ss is eof break
        if(ss.eof()){
            break;
        }

        string pdir,pip,pport,pfl;

        if(!(ss >> pdir>>pip>>pport>>pfl)){
            // something went wrong... no input.
            break;
        }

        // prints packet in. delete later.
        //cout << pdir<<" "<<pip<<" "<<pport<<" "<<pfl<<endl;//del


        //// COMPARE PACKET TO RULES ARRAY ////
        bool foundRuleMatch=false;
        for (unsigned int i = 0; i < ruleNumber; i++){
            if (rules_ptr[i]->assessPacket(pdir, pip, pport, pfl)){
                rules_ptr[i]->printDecision(pdir, pip, pport, pfl);
                foundRuleMatch=true;
                break;
            }
        }

        if(!foundRuleMatch){
            printPacketDropped(pdir, pip, pport, pfl);
        }

    }

    return 0;
}

void Rule::printDecision(string d, string i, string p, string f){
    cout<<this->action_s<<"("<<this->lineNumber<<") "<< d << " " << i << " " << p << " " << f << endl;
}

//input strings: d=direction, i=ip, p=ports, f=flag.
//returns true or false if a rule match is found.
bool Rule::assessPacket(string d, string i, string p, string f){

    // first attempt to convert the ip to hex.
    uint32_t ip_hex = NULL;
    //cout<<"ip_hex should be some number: "<<ip_hex<<endl;
    if(!this->convertStringIPtoHEX(i, ip_hex)){
        //if didnt convert ip then drop packet.
        return false;
    }
    //cout<<"ip_hex should be some NEW number: "<<ip_hex<<endl;

    // if d == direction
    ///AND ip is MATCHED
    ////AND port is on list
    /////AND if packet matches established...
    //////preform action.

    if(!this->direction_s.compare(d)){
        // if the directions match then got here.

        if(this->compareIPs(ip_hex)){
            // if the ips matched then got here.

            //if a the packet port is on the list of the rule
            if(this->comparePorts(p)){
                // if the ports matched got here.


                // if the packet is marked established:
                if(!f.compare("1")){
                    // check if the rule was also established
                    if(this->flag){
                        // if the rule is est, and the packet is est, then this rule applies.
                        return true;
                    }
                    else{
                        // if the packet is established, then weather the rule requires established or not, allow.
                        return true;
                    }
                }
                // if the packet was 0:
                else{
                    //if the packet is NOT established but the rule IS, then this rule does not apply.
                    if(this->flag){
                        return false;
                    }
                    //if the packet is not established and the rule is not established. then allow.
                    else{
                        return true;
                    }
                }
            }
        }
    }

    // if the packet does not fully match a rule return false.
    return false;
}


// checks if the port in the packet matches the port(s) in the rule. if yes return true.
bool Rule::comparePorts(string packet_port){
    //cout<<"got to check ports"<<endl;

    // if the rule port is wildcard * return true.
    if (!this->port_s.compare("*")){
        return true;
    }

    // setup the parsing of the port strings.
    uint16_t p; // range 0 -> 65535
    istringstream pss(packet_port);
    istringstream ss(this->port_s);
    char ch;
    uint16_t rule_port;

    // if the packet port can not be read as an uint16_t then return false, will be dropped.
    if(!(pss>>p)){
        //cout<<"SHOULD NEVER HAVE AN EMPTY PORT NUMBER";
        return false;
    }

    // if the packet port is on the list of ports in the rule return true.
    while(ss>>rule_port){
        ss>>ch;
        if(rule_port == p){
            return true;
        }
    }

    // if no ports on the rule list match, return false.
    return false;
}

// checks if the ip in the packet matches the ip in the rule. if yes return true.
bool Rule::compareIPs(uint32_t p_ip){

    // if the rule is a wildcard * then just return true.
    if (!this->ip_s.compare("*")){
        //cout<<"IPRULE:STAR:TRUE"//del
        return true;
    }

    // if the CIDR tag does not equal the impossible sentinal default value.
    if (this->cidrTag != -999){
        // then it had a CIDR tag. So netmask both ips and compare.
        uint32_t rule_IP = this->ip & this->netmask;
        uint32_t packet_IP = p_ip & this->netmask;

        //if they match return true
        if(rule_IP == packet_IP){
            //cout<<"MATCH: C:"<<cidrTag<<" NM:"<<hex<<netmask<<"  ip:"<<ip<<" pip:"<<p_ip;//del
            return true;
        }
        else{
            //cout<<"IPRULE: HEXES DIDNT MATCH";
            return false;
        }
    }
    else{
        //else the ip didnt have a cidr tag

        //if the ips match return true.
        if(this->ip == p_ip){
            return true;
        }
        else{
            return false;
        }
    }
}

// converts sting ip of form a.b.c.d into hex representation (UINT32).
// returns true or false if able to convert the string from expected a.b.c.d representation to hex.
bool Rule::convertStringIPtoHEX(string ip_string, uint32_t& ip_hex){
    char ch;
    uint32_t a,b,c,d;
    istringstream ss(ip_string);
    if(!(ss>>a>>ch>>b>>ch>>c>>ch>>d)){
        //if can not convert string drop the packet.
        //cout<<"SHOULD NEVER SEE CAN NOT CONVERT STRING TO HEX!!"<<endl;//del
        return false;
    }
    ip_hex = (a<<24)+(b<<16)+(c<<8)+d;
    return true;
}
