#include "tweetoscopeCollectorParams.hpp"
#include <cppkafka/cppkafka.h>

int main(int argc, char *argv[])
{

    if (argc != 2)
    {
        std::cout << "Usage : " << argv[0] << " <config-filename>" << std::endl;
        return 0;
    }
    tweetoscope::params::collector params(argv[1]);
    std::cout << std::endl
              << "Parameters : " << std::endl
              << "----------" << std::endl
              << std::endl
              << params.kafka.brokers << std::endl
              << std::endl;
    return 0;
}