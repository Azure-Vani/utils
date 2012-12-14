data Info = Info {l :: Int, r :: Int, size :: Int} deriving(Show, Read)
data Tree a = Empty | Node a (Tree a) (Tree a) deriving(Show, Read)
type SegTree = Tree Info
maxN = 1000

getsize :: SegTree->Int
getsize Empty = 0
getsize (Node a ch0 ch1) = size a

build :: Int->Int->SegTree
build l' r' 
	| l' == r' = Node Info{l = l', r = r', size = 0} Empty Empty
	| l' < r' = Node Info{l = l', r = r', size = 0} (build l' mid) (build (mid + 1) r')
	where mid = div (l' + r') 2

insert :: Int->SegTree->Int->SegTree
insert x Empty flag = Empty
insert x (Node a ch0 ch1) flag
	| x <= mid = Node na (insert x ch0 flag) ch1
	| otherwise = Node na ch0 (insert x ch1 flag)
	where mid = div ((l a) + (r a)) 2
	      na = Info{l = l a, r = r a, size = (size a) + flag}

calculate :: Int->SegTree->Int
calculate x Empty = 0
calculate x (Node a ch0 ch1)
	| x <= mid = calculate x ch0
	| otherwise = (calculate x ch1) + (getsize ch0)
	where mid = div ((l a) + (r a)) 2

work :: ([Int], SegTree)->String->([Int], SegTree)
work (a, Empty) _ = (a, Empty)
work (res, a) st
	| tmp == "ins" = (res, insert x a 1)
	| tmp == "cal" = (res ++ [calculate (x + 1) a], a)
	| tmp == "del" = (res, insert x a (-1))
	| tmp == "quit" = (res, a)
	where tmp = words st !! 0
	      x = read $ words st !! 1 :: Int

main = interact $ concatMap((++"\n").show).fst.(foldl work ([], build 1 maxN)).lines
