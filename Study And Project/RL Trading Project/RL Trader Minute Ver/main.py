import os
import sys
import logging
import argparse
import json

import settings
import utils
import data_manager
group1 = ['265520', '035760', '058820', '028150', '035900', '035600', '060720', '060250', '030190', '178920', '218410', '036540', '036490', '098460', '215000', '078130', '092730', '007390', '033640', '194700', '144510', '031390', '119860', '032190', '068240', '045390', '078600', '213420', '100130', '086450']
group2 = ['005290', '025900', '060570', '141080', '294140', '058470', '267980', '215200', '235980', '086900', '078160', '140410', '018290', '090460', '082920', '143240', '000250', '038500', '038540', '089980', '006730', '092190', '046890', '178320', '268600', '068760', '091990', '357780', '036830', '192440']
group3 = ['253450', '243840', '108320', '222080', '096530', '025980', '092040', '084850', '067160', '053800', '065660', '131370', '196170', '101490', '056190', '041510', '052020', '237690', '298380', '088800', '028300', '067630', '239610', '230360', '086520', '247540', '183490', '182400', '061970', '290650']
group4 = ['066970', '097520', '039200', '048260', '138080', '122990', '122870', '240810', '104830', '030530', '069080', '044340', '112040', '078070', '023410', '084370', '263050', '272290', '078020', '102710', '039030', '035810', '060150', '048530', '095700', '204270', '036930', '115450', '085660', '278280']
group5 = ['293490', '042000', '078340', '214370', '032500', '290510', '041960', '029960', '033290', '200130', '083790', '214150', '237880', '095610', '200230', '108230', '064760', '034230', '214450', '091700', '263750', '022100', '137400', '003380', '034950', '084990', '048410', '052260', '243070', '145020']
group = group1+group2+group3+group4+group5
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stock_code', nargs='+', default=group)
    parser.add_argument('--ver', choices=['v1', 'v2'], default='v1')
    parser.add_argument('--rl_method',
                        choices=['dqn', 'pg', 'ac', 'a2c', 'a3c', 'monkey'])
    parser.add_argument('--net',
                        choices=['dnn', 'lstm', 'cnn', 'monkey'], default='dnn')
    parser.add_argument('--num_steps', type=int, default=1)
    parser.add_argument('--lr', type=float, default=0.01)
    parser.add_argument('--discount_factor', type=float, default=0.9)
    parser.add_argument('--start_epsilon', type=float, default=0)
    parser.add_argument('--balance', type=int, default=10000000)
    parser.add_argument('--num_epoches', type=int, default=100)
    parser.add_argument('--delayed_reward_threshold',
                        type=float, default=0.05)
    parser.add_argument('--backend',
                        choices=['tensorflow', 'plaidml'], default='tensorflow')
    parser.add_argument('--output_name', default=utils.get_time_str())
    parser.add_argument('--value_network_name')
    parser.add_argument('--policy_network_name')
    parser.add_argument('--reuse_models', action='store_true')
    parser.add_argument('--learning', action='store_true')
    parser.add_argument('--start_date', default='202106130800')
    parser.add_argument('--end_date', default='202106171100')
    args = parser.parse_args()

    # Keras Backend 설정
    if args.backend == 'tensorflow':
        os.environ['KERAS_BACKEND'] = 'tensorflow'
    elif args.backend == 'plaidml':
        os.environ['KERAS_BACKEND'] = 'plaidml.keras.backend'

    # 출력 경로 설정
    output_path = os.path.join(settings.BASE_DIR,
                               'output/{}_{}_{}'.format(args.output_name, args.rl_method, args.net))
    if not os.path.isdir(output_path):
        os.makedirs(output_path)

    # 파라미터 기록
    with open(os.path.join(output_path, 'params.json'), 'w') as f:
        f.write(json.dumps(vars(args)))

    # 로그 기록 설정
    file_handler = logging.FileHandler(filename=os.path.join(
        output_path, "{}.log".format(args.output_name)), encoding='utf-8')
    stream_handler = logging.StreamHandler(sys.stdout)
    file_handler.setLevel(logging.DEBUG)
    stream_handler.setLevel(logging.INFO)
    logging.basicConfig(format="%(message)s",
                        handlers=[file_handler, stream_handler], level=logging.DEBUG)

    # 로그, Keras Backend 설정을 먼저하고 RLTrader 모듈들을 이후에 임포트해야 함
    from agent import Agent
    from learners import ReinforcementLearner, DQNLearner, \
        PolicyGradientLearner, ActorCriticLearner, A2CLearner, A3CLearner

    # 모델 경로 준비
    value_network_path = ''
    policy_network_path = ''
    if args.value_network_name is not None:
        value_network_path = os.path.join(settings.BASE_DIR,
                                          'models/{}.h5'.format(args.value_network_name))
    else:
        value_network_path = os.path.join(
            output_path, '{}_{}_value_{}.h5'.format(
                args.rl_method, args.net, args.output_name))
    if args.policy_network_name is not None:
        policy_network_path = os.path.join(settings.BASE_DIR,
                                           'models/{}.h5'.format(args.policy_network_name))
    else:
        policy_network_path = os.path.join(
            output_path, '{}_{}_policy_{}.h5'.format(
                args.rl_method, args.net, args.output_name))

    common_params = {}
    list_stock_code = []
    list_chart_data = []
    list_training_data = []
    list_min_trading_unit = []
    list_max_trading_unit = []

    for stock_code in args.stock_code:
        # 차트 데이터, 학습 데이터 준비
        chart_data, training_data = data_manager.load_data(
            os.path.join(settings.BASE_DIR,
                         'data/{}/{}.csv'.format(args.ver, stock_code)),
            args.start_date, args.end_date, ver=args.ver)
        print(chart_data)
        print("-------------------")
        print(len(chart_data))
        print("----------------")
        print(chart_data)

        # 최소/최대 투자 단위 설정
        min_trading_unit = max(int(100000 / chart_data.iloc[-1]['close']), 1)
        max_trading_unit = max(int(1000000 / chart_data.iloc[-1]['close']), 1)

        # 공통 파라미터 설정
        common_params = {'rl_method': args.rl_method,
                         'delayed_reward_threshold': args.delayed_reward_threshold,
                         'net': args.net, 'num_steps': args.num_steps, 'lr': args.lr,
                         'output_path': output_path, 'reuse_models': args.reuse_models}

        # 강화학습 시작
        learner = None
        if args.rl_method != 'a3c':
            common_params.update({'stock_code': stock_code,
                                  'chart_data': chart_data,
                                  'training_data': training_data,
                                  'min_trading_unit': min_trading_unit,
                                  'max_trading_unit': max_trading_unit})
            if args.rl_method == 'dqn':
                learner = DQNLearner(**{**common_params,
                                        'value_network_path': value_network_path})
            elif args.rl_method == 'pg':
                learner = PolicyGradientLearner(**{**common_params,
                                                   'policy_network_path': policy_network_path})
            elif args.rl_method == 'ac':
                learner = ActorCriticLearner(**{**common_params,
                                                'value_network_path': value_network_path,
                                                'policy_network_path': policy_network_path})
            elif args.rl_method == 'a2c':
                learner = A2CLearner(**{**common_params,
                                        'value_network_path': value_network_path,
                                        'policy_network_path': policy_network_path})
            elif args.rl_method == 'monkey':
                args.net = args.rl_method
                args.num_epoches = 1
                args.discount_factor = None
                args.start_epsilon = 1
                args.learning = False
                learner = ReinforcementLearner(**common_params)
            if learner is not None:
                learner.run(balance=args.balance,
                            num_epoches=args.num_epoches,
                            discount_factor=args.discount_factor,
                            start_epsilon=args.start_epsilon,
                            learning=args.learning)
                learner.save_models()
        else:
            list_stock_code.append(stock_code)
            list_chart_data.append(chart_data)
            list_training_data.append(training_data)
            list_min_trading_unit.append(min_trading_unit)
            list_max_trading_unit.append(max_trading_unit)

    if args.rl_method == 'a3c':
        learner = A3CLearner(**{
            **common_params,
            'list_stock_code': list_stock_code,
            'list_chart_data': list_chart_data,
            'list_training_data': list_training_data,
            'list_min_trading_unit': list_min_trading_unit,
            'list_max_trading_unit': list_max_trading_unit,
            'value_network_path': value_network_path,
            'policy_network_path': policy_network_path})

        learner.run(balance=args.balance, num_epoches=args.num_epoches,
                    discount_factor=args.discount_factor,
                    start_epsilon=args.start_epsilon,
                    learning=args.learning)
        learner.save_models()
