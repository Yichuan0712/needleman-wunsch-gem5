#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define DEFAULT_MATCH_SCORE 2
#define DEFAULT_MISMATCH_PENALTY -1
#define DEFAULT_GAP_PENALTY -2

static inline int max3(int a, int b, int c)
{
    int max = a;
    if (b > max)
        max = b;
    if (c > max)
        max = c;
    return max;
}

// Tiled NW Alignment
void nw_align_tiled(int n, const char *seq1, const char *seq2, int block_size,
                    int match_score, int mismatch_penalty, int gap_penalty)
{
    int rows = n + 1;
    int cols = n + 1;
    int *score = (int *)malloc(rows * cols * sizeof(int));
    if (!score)
        return;

    for (int i = 0; i < rows; i++)
        score[i * cols] = i * gap_penalty;
    for (int j = 0; j < cols; j++)
        score[j] = j * gap_penalty;

    // Outer loops: Iterate over tiles
    for (int bi = 1; bi < rows; bi += block_size)
    {
        for (int bj = 1; bj < cols; bj += block_size)
        {

            // Inner loops: Iterate within a tile
            int i_limit = (bi + block_size < rows) ? bi + block_size : rows;
            int j_limit = (bj + block_size < cols) ? bj + block_size : cols;

            for (int i = bi; i < i_limit; i++)
            {
                for (int j = bj; j < j_limit; j++)
                {
                    int match = score[(i - 1) * cols + (j - 1)] +
                                (seq1[i - 1] == seq2[j - 1] ? match_score : mismatch_penalty);
                    int delete = score[(i - 1) * cols + j] + gap_penalty;
                    int insert = score[i * cols + (j - 1)] + gap_penalty;
                    score[i * cols + j] = max3(match, delete, insert);
                }
            }
        }
    }

    printf("Final Score: %d (Block Size: %d)\n", score[rows * cols - 1], block_size);
    free(score);
}

int main(int argc, char *argv[])
{
    int n = 128;
    int block_size = 1;
    int match_score = DEFAULT_MATCH_SCORE;
    int mismatch_penalty = DEFAULT_MISMATCH_PENALTY;
    int gap_penalty = DEFAULT_GAP_PENALTY;
    unsigned int random_seed = 42;

    if (argc > 1)
        n = atoi(argv[1]);
    if (argc > 2)
        block_size = atoi(argv[2]);
    if (argc > 3)
        match_score = atoi(argv[3]);
    if (argc > 4)
        mismatch_penalty = atoi(argv[4]);
    if (argc > 5)
        gap_penalty = atoi(argv[5]);
    if (argc > 6)
        random_seed = (unsigned int)atoi(argv[6]);

    char *s1 = (char *)malloc(n);
    char *s2 = (char *)malloc(n);
    srand(random_seed);
    for (int i = 0; i < n; i++)
    {
        s1[i] = "ATCG"[rand() % 4];
        s2[i] = "ATCG"[rand() % 4];
    }

    nw_align_tiled(n, s1, s2, block_size, match_score, mismatch_penalty, gap_penalty);

    free(s1);
    free(s2);
    return 0;
}