import torch
import torch.nn.functional as F
import torch.optim as optim
import gym
from a3c_model import ActorCritic
from torch.autograd import Variable
import time
from collections import deque


def test(rank, args, shared_model, dtype):
    torch.manual_seed(args.seed + rank)

    env = gym.make(args.env_name)
    env.seed(args.seed + rank)

    model = ActorCritic(env.observation_space.shape[0], env.action_space).type(dtype)

    model.eval()

    state = env.reset()
    state = torch.from_numpy(state).type(dtype)
    reward_sum = 0
    done = True

    start_time = time.time()

    # a quick hack to prevent the agent from stucking
    actions = deque(maxlen=100)
    episode_length = 0
    while True:
        episode_length += 1
        # Sync with the shared model
        if done:
            model.load_state_dict(shared_model.state_dict())
            cx = Variable(torch.zeros(1, 256).type(dtype), volatile=True)
            hx = Variable(torch.zeros(1, 256).type(dtype), volatile=True)
        else:
            cx = Variable(cx.data.type(dtype), volatile=True)
            hx = Variable(hx.data.type(dtype), volatile=True)

        value, logit, (hx, cx) = model(
            (Variable(state.unsqueeze(0), volatile=True), (hx, cx)))
        prob = F.softmax(logit)
        action = prob.max(1)[1].data.cpu().numpy()

        state, reward, done, _ = env.step(action[0, 0])
        done = done or episode_length >= args.max_episode_length
        reward_sum += reward

        # a quick hack to prevent the agent from stucking
        actions.append(action[0, 0])
        if actions.count(actions[0]) == actions.maxlen:
            done = True

        if done:
            print("Time {}, episode reward {}, episode length {}".format(
                time.strftime("%Hh %Mm %Ss",
                              time.gmtime(time.time() - start_time)),
                reward_sum, episode_length))
            reward_sum = 0
            episode_length = 0
            actions.clear()
            state = env.reset()
            time.sleep(60)

        state = torch.from_numpy(state).type(dtype)