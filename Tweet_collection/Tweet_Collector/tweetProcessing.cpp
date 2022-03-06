#include "tweetProcessing.hpp"

std::ostream &tweetoscope::cascade::operator<<(std::ostream &os, std::vector<std::pair<timestamp, double>> &vect)
{
    os << '[';

    for (auto it = vect.begin(); (it != (vect.end() - 1)); ++it)
    {
        os << " [" << (it)->first << ',' << (it)->second << "] ,";
    }
    auto it = (vect.end() - 1);

    os << " [" << (it)->first << ',' << (it)->second << "] ";

    os << "]";
    return os;
};

bool tweetoscope::cascade::cascade_ref_comparator::operator()(cascade_ref cascade1, cascade_ref cascade2) const
{
    return *cascade1 < *cascade2;
};

tweetoscope::cascade::Cascade::Cascade(tweet &twt, std::string &key) : cid(key),
                                                                       msg(twt.msg),
                                                                       time_first_twt(twt.time),
                                                                       time_last_twt(twt.time),
                                                                       source(twt.source),
                                                                       tweets({std::make_pair(twt.time, twt.magnitude)}){};

void tweetoscope::cascade::Cascade::cascade_update(tweet &twt, std::string &key)
{
    tweets.push_back(std::make_pair(twt.time, twt.magnitude));
    time_last_twt = twt.time;
};

bool tweetoscope::cascade::Cascade::operator<(const Cascade &cascade) const { return time_last_twt < cascade.time_last_twt; }

std::ostringstream tweetoscope::cascade::Cascade::make_size()
{
    std::ostringstream ostr;
    ostr << "{"
         << "\"type\": "
         << "\"size\", "
         << "\"cid\":" << cid
         << ", \"n_tot\":" << tweets.size()
         << ", \"t_end\":" << (time_last_twt)
         << '}';

    return ostr;
};
std::ostringstream tweetoscope::cascade::Cascade::make_serie(timestamp source_time, timestamp observation)
{
    std::ostringstream ostr;
    std::vector<std::pair<timestamp, double>> partial_tweets;
    for (auto it = tweets.begin(); (it->first - time_first_twt <= observation) && (it != tweets.end()); ++it)
    {
        auto time = it->first - time_first_twt;

        partial_tweets.push_back(std::make_pair(time, it->second));
    }
    ostr << "{"
         << "\"type\": "
         << "\"serie\", "
         << "\"cid\":" << cid
         << ", \"msg\":  \"msg\""

         << ", \"T_obs\":" << observation
         << ", \"tweets\":" << partial_tweets
         << '}';

    return ostr;
};

tweetoscope::cascade::Processor::Processor(tweet &twt) : source(twt.source),
                                                         first_tweet(twt.time),
                                                         source_time(twt.time),
                                                         newest_source_time(twt.time),
                                                         cascade_queue{},
                                                         fifo{},
                                                         symbol_table{} {};
void tweetoscope::cascade::Processor::update_newest_source_time(tweet &twt)
{
    newest_source_time = twt.time;
};
void tweetoscope::cascade::Processor::decrease_priority(priority_queue::handle_type location, cascade_ref ref_cascade)
{
    return cascade_queue.decrease(location, ref_cascade);
};

auto tweetoscope::cascade::Processor::update_queue(cascade_ref ref_cascade)
{
    return cascade_queue.push(ref_cascade);
};

bool tweetoscope::cascade::Processor::terminated(timestamp &t_terminated, cascade_ref ref_cascade, bool observation)
{
    if (observation)
        return ((source_time - first_tweet) > t_terminated);
    else
    {
        if ((newest_source_time - source_time) > t_terminated)
        {
            return true;
        }
        else
        {
            source_time = newest_source_time;
            return false;
        }
    }
};
std::vector<std::string> tweetoscope::cascade::Processor::send_partial_cascade(std::vector<timestamp> observations)
{
    std::vector<std::string> data;
    for (auto observation : observations)
    {
        if (!fifo[observation].empty())
        {
            cascade_wck wck_cascade = fifo[observation].front();
            auto ref_cascade = wck_cascade.lock();
            while (terminated(observation, ref_cascade, true)) // while the duration from the first event until the current timestamp is greater than the observation window we create partial cascade
            {
                std::ostringstream ostr = ref_cascade->make_serie(source_time, observation);
                data.push_back(ostr.str());
                fifo[observation].pop();

                if (!fifo[observation].empty())
                {
                    cascade_wck wck_cascade = fifo[observation].front();
                    auto ref_cascade = wck_cascade.lock();
                }
                else
                {
                    break;
                }
            }
        }
    }
    return data;
};
std::vector<std::string> tweetoscope::cascade::Processor::send_terminated_cascade(timestamp &t_terminated, std::size_t min_cascade_size)
{
    std::vector<std::string> data;
    if (!cascade_queue.empty())
    {
        auto ref_cascade = cascade_queue.top();
        while (terminated(t_terminated, ref_cascade))
        {
            if (ref_cascade->tweets.size() > min_cascade_size)
            {
                std::ostringstream ostr = ref_cascade->make_size();
                // cascade_properties { 'type' : 'size', 'cid': 'tw23981', 'n_tot': 127, 't_end': 4329 }
                data.push_back(ostr.str());
                ref_cascade.reset();
            }

            cascade_queue.pop();
            if (!cascade_queue.empty())
            {
                ref_cascade = cascade_queue.top();
            }
            else
            {
                return data;
            }
        };
    }
    return data;
};
